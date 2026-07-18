from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from contracts import ArchitectureContract
from config import settings

OLLAMA_CHAT_URL = settings.ollama_chat_url

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["complete", "reason", "block"],
    "properties": {
        "complete": {"type": "boolean"},
        "reason": {"type": "string"},
        "block": {"anyOf": [{"type": "object"}, {"type": "null"}]},
    },
}

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["approved", "summary", "requirements", "required_fixes"],
    "properties": {
        "approved": {"type": "boolean"},
        "summary": {"type": "string"},
        "requirements": {"type": "array"},
        "required_fixes": {"type": "array", "items": {"type": "string"}},
    },
}
def ollama_structured(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "format": schema,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "temperature": 0.1,
        },
    }

    request = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw_response = response.read().decode("utf-8")
    except urllib.error.URLError as error:
        raise RuntimeError(
            "Could not contact Ollama."
        ) from error

    try:
        response_data = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Ollama returnerade ogiltig JSON i HTTP-svaret."
        ) from error

    content = response_data.get("message", {}).get("content", "").strip()


    if not content:
        raise RuntimeError(
            "Ollama returnerade ett tomt svar."
        )

    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Ollama returned invalid structured JSON in message.content."
        ) from error


def create_next_block(
    *,
    model: str,
    task: str,
    state: dict[str, Any],
    project_snapshot: str,
) -> dict[str, Any]:
    system_prompt = """
You are the planning component of a software-development orchestrator.

Create exactly one small, independently verifiable work block.

Rules:
- Do not write code.
- Do not combine several architectural changes into one block.
- Respect dependencies and previously completed blocks.
- Do not repeat completed work.
- Prefer work that can be completed in one Aider invocation.
- Use concrete project-relative file paths.
- Include new file paths when a new file is required.
- Mark complete=true only when every original requirement is implemented
  and verified.
- When complete=true, block must be null.
"""

    user_prompt = f"""
ORIGINAL TASK:

{task}

CURRENT PROGRESS:

{json.dumps(state, indent=2, ensure_ascii=False)}

CURRENT PROJECT STATUS:

{project_snapshot}

Produce the next work block as JSON matching the supplied schema.
"""

    return ollama_structured(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=PLAN_SCHEMA,
    )


def review_block(
    *,
    model: str,
    task: str,
    block: dict[str, Any],
    diff: str,
    verification: dict[str, Any],
    protected_violations: list[str],
    architecture_contract: ArchitectureContract | None = None,
    contract_violations: list[str] | None = None,
) -> dict[str, Any]:
    system_prompt = """
You are a strict software change reviewer.

Review only the current work block.

Approval rules:
- Every block requirement must have concrete evidence.
- All deterministic verification commands must pass.
- Protected files must not be changed.
- The implementation must satisfy the architecture contract exactly.
- Files outside allowed_files must not be changed.
- Do not redesign the architecture during review.
- Do not approve based on the implementer's claims.
- Use only the supplied changes and verification output as evidence.
- If evidence is missing, status must be unknown or fail.
- approved may be true only when there are no fail or unknown items.
"""

    contract_text = (
        json.dumps(architecture_contract.to_dict(), indent=2, ensure_ascii=False)
        if architecture_contract
        else "No architecture contract supplied."
    )
    contract_violations = contract_violations or []

    user_prompt = f"""
ORIGINAL TASK:

{task}

CURRENT BLOCK:

{json.dumps(block, indent=2, ensure_ascii=False)}

ARCHITECTURE CONTRACT:

{contract_text}

CONTRACT VIOLATIONS:

{json.dumps(contract_violations, indent=2, ensure_ascii=False)}

PROTECTED-PATH VIOLATIONS:

{json.dumps(protected_violations, indent=2)}

VERIFICATION:

{json.dumps(verification, indent=2, ensure_ascii=False)}

PROJECT CHANGES:

{diff}
"""

    return ollama_structured(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=REVIEW_SCHEMA,
    )
