from __future__ import annotations

import json
from typing import Any

from contracts import ArchitectureContract
from ollama_workflow import ollama_structured


ARCHITECTURE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "id",
        "goal",
        "summary",
        "allowed_files",
        "forbidden_files",
        "required_changes",
        "preserved_api",
        "removed_api",
        "risks",
        "acceptance",
    ],
    "properties": {
        "id": {"type": "string"},
        "goal": {"type": "string"},
        "summary": {"type": "string"},
        "allowed_files": {"type": "array", "items": {"type": "string"}},
        "forbidden_files": {"type": "array", "items": {"type": "string"}},
        "required_changes": {"type": "array", "items": {"type": "string"}},
        "preserved_api": {"type": "array", "items": {"type": "string"}},
        "removed_api": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "acceptance": {"type": "array", "items": {"type": "string"}},
    },
}


def create_architecture_contract(
    *,
    model: str,
    task: str,
    block: dict[str, Any],
    project_snapshot: str,
    config: dict[str, Any] | None = None,
) -> ArchitectureContract:
    """Design one block and produce the formal Builder/Reviewer handoff."""

    config = config or {}
    system_prompt = """
You are the Architect in an AI software-development organization.

Your responsibility is system design and a precise implementation contract.
You do not write code and you do not perform the Builder's work.

Rules:
- Design only the supplied work block, not later work.
- Resolve architectural ambiguity before handing work to Builder.
- Preserve existing behavior and public APIs unless removal is explicit.
- Name every file Builder may modify in allowed_files.
- Put files that must remain untouched in forbidden_files.
- required_changes must be concrete, independently verifiable actions.
- acceptance must be objective and testable.
- Do not tell Builder to make architectural choices.
- Builder must be able to implement the contract without knowing product vision.
- If the block is contradictory, make the contradiction explicit in summary and
  acceptance rather than silently inventing product requirements.
"""

    user_prompt = f"""
ORIGINAL PRODUCT TASK:

{task}

PLANNER WORK BLOCK:

{json.dumps(block, indent=2, ensure_ascii=False)}

PROJECT SNAPSHOT:

{project_snapshot}

PROCESS CONSTRAINTS:

{json.dumps(config, indent=2, ensure_ascii=False)}

Produce one architecture contract matching the supplied schema.
"""

    data = ollama_structured(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=ARCHITECTURE_SCHEMA,
    )
    contract = ArchitectureContract.from_dict(data)
    _validate_contract_scope(contract=contract, block=block, config=config)
    return contract


def _validate_contract_scope(
    *,
    contract: ArchitectureContract,
    block: dict[str, Any],
    config: dict[str, Any],
) -> None:
    planned_files = block.get("files", [])
    if not isinstance(planned_files, list) or not all(
        isinstance(path, str) for path in planned_files
    ):
        raise ValueError("Planner block files must be an array of strings")

    # Architect may narrow scope, but may not silently expand beyond Planner.
    unplanned = set(contract.allowed_files) - set(planned_files)
    if unplanned:
        raise ValueError(
            "Architect allowed files outside Planner block: "
            + ", ".join(sorted(unplanned))
        )

    max_files = config.get("max_files_to_modify")
    if max_files is not None and len(contract.allowed_files) > int(max_files):
        raise ValueError(
            "Architecture contract exceeds max_files_to_modify: "
            f"{len(contract.allowed_files)} > {int(max_files)}"
        )
