from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
NIGHTSHIFT = ROOT / "nightshift"
STATE_DIR = NIGHTSHIFT / "state"
REPORT_DIR = NIGHTSHIFT / "reports"

CONFIG_PATH = NIGHTSHIFT / "config.json"
TASK_PATH = NIGHTSHIFT / "task.md"
STATE_PATH = STATE_DIR / "progress.json"

OLLAMA_URL = "http://localhost:11434/api/chat"


@dataclass
class CommandResult:
    command: str
    return_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0

    def combined_output(self, max_chars: int = 20_000) -> str:
        output = f"{self.stdout}\n{self.stderr}".strip()
        return output[-max_chars:]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=False)

    temporary.replace(path)


def run_command(
    command: str,
    *,
    timeout_seconds: int,
) -> CommandResult:
    print(f"\n$ {command}", flush=True)

    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )

        if completed.stdout:
            print(completed.stdout, flush=True)

        if completed.stderr:
            print(completed.stderr, file=sys.stderr, flush=True)

        return CommandResult(
            command=command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        return CommandResult(
            command=command,
            return_code=124,
            stdout=str(stdout),
            stderr=f"{stderr}\nCommand timed out.",
        )


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
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "options": {
            "temperature": 0.1
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError(
            "Could not contact Ollama at http://localhost:11434."
        ) from error

    content = response_data["message"]["content"]

    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Ollama returned invalid JSON:\n{content}"
        ) from error


def git_status() -> str:
    result = run_command(
        "git status --short",
        timeout_seconds=30,
    )
    return result.stdout.strip()


def git_diff() -> str:
    result = run_command(
        "git diff --no-ext-diff --unified=80",
        timeout_seconds=60,
    )
    return result.stdout


def changed_files() -> list[str]:
    result = run_command(
        "git diff --name-only",
        timeout_seconds=30,
    )

    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def detect_protected_changes(
    files: list[str],
    protected_paths: list[str],
) -> list[str]:
    violations: list[str] = []

    for filename in files:
        for protected in protected_paths:
            protected_normalized = protected.rstrip("/")

            if (
                filename == protected_normalized
                or filename.startswith(protected_normalized + "/")
            ):
                violations.append(filename)

    return sorted(set(violations))


PLAN_SCHEMA = {
    "type": "object",
    "required": ["complete", "reason", "block"],
    "properties": {
        "complete": {
            "type": "boolean"
        },
        "reason": {
            "type": "string"
        },
        "block": {
            "type": ["object", "null"],
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "objective": {"type": "string"},
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "verification": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": [
                "id",
                "title",
                "objective",
                "requirements",
                "files",
                "verification"
            ]
        }
    }
}


REVIEW_SCHEMA = {
    "type": "object",
    "required": [
        "approved",
        "summary",
        "requirements",
        "required_fixes"
    ],
    "properties": {
        "approved": {
            "type": "boolean"
        },
        "summary": {
            "type": "string"
        },
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "requirement",
                    "status",
                    "evidence"
                ],
                "properties": {
                    "requirement": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pass", "fail", "unknown"]
                    },
                    "evidence": {"type": "string"}
                }
            }
        },
        "required_fixes": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}


def create_next_block(
    *,
    model: str,
    task: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    system_prompt = """
You are the planning component of a software-development orchestrator.

Create exactly one small, independently verifiable work block.

Rules:
- Do not write code.
- Do not combine several architectural changes into one block.
- Respect dependencies and previously completed blocks.
- Do not repeat completed work.
- Prefer a block that can be completed in one Aider invocation.
- Use concrete file paths when they can be inferred.
- Mark complete=true only when every original requirement has been
  implemented and verified.
"""

    user_prompt = f"""
ORIGINAL TASK:

{task}

CURRENT PROGRESS:

{json.dumps(state, indent=2, ensure_ascii=False)}

Produce the next work block.
"""

    return ollama_structured(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=PLAN_SCHEMA,
    )


def build_aider_prompt(
    *,
    task: str,
    block: dict[str, Any],
    attempt: int,
    previous_review: dict[str, Any] | None,
) -> str:
    review_text = (
        json.dumps(previous_review, indent=2, ensure_ascii=False)
        if previous_review
        else "No previous review. This is the first attempt."
    )

    return f"""
Implement only the current work block.

Do not implement later blocks.
Do not commit, push, merge, rebase, or reset Git history.
Do not weaken, delete, skip, or disable existing tests.
Do not alter test commands to hide failures.
Do not claim that a command passed unless it was actually executed.

ORIGINAL FEATURE:

{task}

CURRENT BLOCK:

{json.dumps(block, indent=2, ensure_ascii=False)}

ATTEMPT:

{attempt}

REVIEW FROM PREVIOUS ATTEMPT:

{review_text}

Before finishing:

1. Inspect all relevant existing code.
2. Implement every requirement in the current block.
3. Add or update tests when needed.
4. Run the applicable tests and type checks.
5. Inspect the final diff.
6. Correct problems before stopping.
7. Report what changed and which commands were actually executed.
"""


def run_aider(
    *,
    config: dict[str, Any],
    prompt: str,
    block: dict[str, Any],
) -> CommandResult:
    timeout_seconds = (
        int(config["timeout_minutes_per_aider_run"]) * 60
    )

    arguments = [
        "aider",
        "--model",
        config["aider_model"],
        "--message",
        prompt,
        "--no-stream",
        "--yes-always",
        "--no-auto-commits",
    ]

    test_command = config["commands"].get("test")
    if test_command:
        arguments.extend([
            "--test-cmd",
            test_command,
            "--auto-test",
        ])

    # Give Aider only explicitly identified files that already exist.
    for filename in block.get("files", []):
        path = ROOT / filename
        if path.exists() and path.is_file():
            arguments.append(filename)

    # subprocess receives a list here, so task text is not interpreted
    # as shell syntax.
    print("\nStarting Aider...", flush=True)

    try:
        completed = subprocess.run(
            arguments,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )

        print(completed.stdout, flush=True)

        if completed.stderr:
            print(completed.stderr, file=sys.stderr, flush=True)

        return CommandResult(
            command="aider",
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    except subprocess.TimeoutExpired as error:
        return CommandResult(
            command="aider",
            return_code=124,
            stdout=str(error.stdout or ""),
            stderr=f"{error.stderr or ''}\nAider timed out.",
        )


def run_verification(
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}

    for name, command in config["commands"].items():
        if not command:
            continue

        result = run_command(
            command,
            timeout_seconds=20 * 60,
        )

        results[name] = {
            "command": command,
            "return_code": result.return_code,
            "passed": result.passed,
            "output": result.combined_output(),
        }

    return results


def review_block(
    *,
    model: str,
    task: str,
    block: dict[str, Any],
    diff: str,
    verification: dict[str, Any],
    protected_violations: list[str],
) -> dict[str, Any]:
    system_prompt = """
You are a strict software change reviewer.

Review only the current work block.

Approval rules:
- Every block requirement must have concrete evidence.
- All deterministic verification commands must pass.
- Protected files must not be changed.
- Do not approve based on the implementer's claims.
- Use only the supplied diff and verification output as evidence.
- If evidence is missing, status must be unknown or fail.
- approved may be true only when there are no fail or unknown items.
"""

    user_prompt = f"""
ORIGINAL TASK:

{task}

CURRENT BLOCK:

{json.dumps(block, indent=2, ensure_ascii=False)}

PROTECTED-PATH VIOLATIONS:

{json.dumps(protected_violations, indent=2)}

VERIFICATION:

{json.dumps(verification, indent=2, ensure_ascii=False)}

GIT DIFF:

{diff[-60_000:]}
"""

    return ollama_structured(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=REVIEW_SCHEMA,
    )


def write_report(
    block_id: str,
    attempt: int,
    content: dict[str, Any],
) -> None:
    path = REPORT_DIR / f"{block_id}-attempt-{attempt}.json"
    save_json(path, content)


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    config = load_json(CONFIG_PATH)
    task = TASK_PATH.read_text(encoding="utf-8")

    if STATE_PATH.exists():
        state = load_json(STATE_PATH)
    else:
        state = {
            "status": "running",
            "started_at": time.time(),
            "completed_blocks": [],
            "failed_blocks": [],
        }
        save_json(STATE_PATH, state)

    initial_status = git_status()
    if initial_status:
        print(
            "\nERROR: The working tree is not clean.\n"
            "Commit or stash existing work before starting nightshift.\n\n"
            f"{initial_status}",
            file=sys.stderr,
        )
        return 1

    for block_number in range(1, int(config["max_blocks"]) + 1):
        plan = create_next_block(
            model=config["model"],
            task=task,
            state=state,
        )

        if plan["complete"]:
            state["status"] = "completed"
            state["completion_reason"] = plan["reason"]
            save_json(STATE_PATH, state)
            print("\nAll planned work is complete.")
            return 0

        block = plan["block"]
        block_id = block["id"]
        previous_review: dict[str, Any] | None = None

        print(
            f"\n=== Block {block_number}: "
            f"{block_id} — {block['title']} ==="
        )

        block_approved = False

        for attempt in range(
            1,
            int(config["max_attempts_per_block"]) + 1,
        ):
            before_files = changed_files()

            prompt = build_aider_prompt(
                task=task,
                block=block,
                attempt=attempt,
                previous_review=previous_review,
            )

            aider_result = run_aider(
                config=config,
                prompt=prompt,
                block=block,
            )

            files = changed_files()
            newly_changed = sorted(set(files) - set(before_files))

            protected_violations = detect_protected_changes(
                files,
                config["protected_paths"],
            )

            verification = run_verification(config)
            diff = git_diff()

            review = review_block(
                model=config["model"],
                task=task,
                block=block,
                diff=diff,
                verification=verification,
                protected_violations=protected_violations,
            )

            deterministic_pass = (
                aider_result.passed
                and not protected_violations
                and all(
                    result["passed"]
                    for result in verification.values()
                )
            )

            approved = (
                deterministic_pass
                and bool(review["approved"])
            )

            report = {
                "block": block,
                "attempt": attempt,
                "aider_return_code": aider_result.return_code,
                "changed_files": files,
                "newly_changed_files": newly_changed,
                "protected_violations": protected_violations,
                "verification": verification,
                "review": review,
                "approved": approved,
            }

            write_report(block_id, attempt, report)

            if approved:
                state["completed_blocks"].append({
                    "block": block,
                    "attempts": attempt,
                    "changed_files": files,
                    "review": review,
                })
                save_json(STATE_PATH, state)

                print(f"\nBlock {block_id} approved.")
                block_approved = True
                break

            previous_review = review
            print(
                f"\nBlock {block_id} was rejected. "
                f"Attempt {attempt} of "
                f"{config['max_attempts_per_block']}."
            )

        if not block_approved:
            state["status"] = "blocked"
            state["failed_blocks"].append({
                "block": block,
                "last_review": previous_review,
            })
            save_json(STATE_PATH, state)

            print(
                f"\nStopped: block {block_id} could not be approved.",
                file=sys.stderr,
            )
            return 2

    state["status"] = "partial"
    state["reason"] = "Maximum number of blocks reached."
    save_json(STATE_PATH, state)

    print("\nStopped after reaching the configured block limit.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
