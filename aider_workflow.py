from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contracts import ArchitectureContract
from git_tools import git_review_bundle
from orchestrator_runtime import CommandResult, process_environment, run_command, run_shell_command, save_json

NIGHTSHIFT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = NIGHTSHIFT_ROOT / "reports"
def build_aider_prompt(
    *,
    task: str,
    block: dict[str, Any],
    attempt: int,
    previous_review: dict[str, Any] | None,
    architecture_contract: ArchitectureContract | None = None,
) -> str:
    review_text = (
        json.dumps(previous_review, indent=2, ensure_ascii=False)
        if previous_review
        else "No previous review. This is the first attempt."
    )

    contract_text = (
        json.dumps(architecture_contract.to_dict(), indent=2, ensure_ascii=False)
        if architecture_contract
        else "No architecture contract supplied."
    )

    return f"""
You are the Builder. Implement exactly the architecture contract.

Do not redesign the solution or make product decisions.
If the contract is contradictory or insufficient, stop and report the issue.
Implement only the current work block.

Do not implement later blocks.
Do not commit, push, merge, rebase, or reset Git history.
Do not weaken, delete, skip, or disable existing tests.
Do not alter test commands to hide failures.
Do not add dependencies unless the current block explicitly requires it.
Do not claim that a command passed unless it was actually executed.

ORIGINAL FEATURE:

{task}

CURRENT BLOCK:

{json.dumps(block, indent=2, ensure_ascii=False)}

ARCHITECTURE CONTRACT:

{contract_text}

ATTEMPT:

{attempt}

REVIEW FROM PREVIOUS ATTEMPT:

{review_text}

Before finishing:
1. Inspect the relevant existing code.
2. Implement every requirement in the current block.
3. Add or update tests when needed.
4. Run applicable tests and type checks.
5. Inspect the final changes.
6. Correct problems before stopping.
7. Report changed files and commands actually executed.
"""


def run_aider(
    *,
    project_root: Path,
    config: dict[str, Any],
    prompt: str,
    block: dict[str, Any],
    architecture_contract: ArchitectureContract | None = None,
) -> CommandResult:
    timeout_seconds = int(config["timeout_minutes_per_aider_run"]) * 60

    arguments = [
        "aider",
        "--model",
        config["aider_model"],
        "--no-show-model-warnings",
        "--no-pretty",
        "--no-stream",
        "--yes-always",
        "--no-auto-commits",
        "--message",
        prompt,
    ]

    test_command = config.get("commands", {}).get("test")
    if test_command:
        arguments.extend(
            [
                "--test-cmd",
                test_command,
                "--auto-test",
            ]
        )

    # Builder receives only files explicitly allowed by Architect.
    filenames = (
        architecture_contract.allowed_files
        if architecture_contract is not None
        else tuple(block.get("files", []))
    )
    for filename in filenames:
        arguments.append(filename)

    print("\nStarting Aider...", flush=True)

    return run_command(
        arguments,
        cwd=project_root,
        env=process_environment(),
        timeout_seconds=timeout_seconds,
    )


def run_verification(
    *,
    project_root: Path,
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}

    for name, command in config.get("commands", {}).items():
        if not command:
            continue

        result = run_shell_command(
            command,
            cwd=project_root,
            timeout_seconds=20 * 60,
        )

        results[name] = {
            "command": command,
            "return_code": result.return_code,
            "passed": result.passed,
            "output": result.combined_output(),
        }

    diff_check = run_command(
        ["git", "--no-pager", "diff", "--check"],
        cwd=project_root,
        timeout_seconds=60,
    )

    results["git_diff_check"] = {
        "command": "git --no-pager diff --check",
        "return_code": diff_check.return_code,
        "passed": diff_check.passed,
        "output": diff_check.combined_output(),
    }

    return results


def write_report(
    block_id: str,
    attempt: int,
    content: dict[str, Any],
) -> None:
    path = REPORT_DIR / f"{block_id}-attempt-{attempt}.json"
    save_json(path, content)
