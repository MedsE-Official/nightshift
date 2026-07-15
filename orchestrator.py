from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NIGHTSHIFT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = NIGHTSHIFT_ROOT / "config.json"
TASK_PATH = NIGHTSHIFT_ROOT / "task.md"
STATE_DIR = NIGHTSHIFT_ROOT / "state"
REPORT_DIR = NIGHTSHIFT_ROOT / "reports"
STATE_PATH = STATE_DIR / "progress.json"

# Use the settings from config.py instead of hardcoded URLs
from config import settings

OLLAMA_CHAT_URL = settings.ollama_chat_url


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


# Define schemas at the top so they're available to functions that use them
PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["complete", "reason", "block"],
    "properties": {
        "complete": {"type": "boolean"},
        "reason": {"type": "string"},
        "block": {
            "anyOf": [
                {
                    "type": "object",
                    "required": [
                        "id",
                        "title",
                        "objective",
                        "requirements",
                        "files",
                        "verification",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "objective": {"type": "string"},
                        "requirements": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "verification": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                {"type": "null"},
            ]
        },
    },
}


REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "approved",
        "summary",
        "requirements",
        "required_fixes",
    ],
    "properties": {
        "approved": {"type": "boolean"},
        "summary": {"type": "string"},
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["requirement", "status", "evidence"],
                "properties": {
                    "requirement": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pass", "fail", "unknown"],
                    },
                    "evidence": {"type": "string"},
                },
            },
        },
        "required_fixes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=False)

    temporary.replace(path)


def process_environment() -> dict[str, str]:
    env = os.environ.copy()

    # Aider talks to Ollama through Ollama's OpenAI-compatible endpoint.
    env.setdefault("OPENAI_API_BASE", settings.openai_api_base)
    env.setdefault("OPENAI_API_KEY", "ollama")

    # Prevent pagers and alternate terminal screens during unattended runs.
    env["PAGER"] = "cat"
    env["GIT_PAGER"] = "cat"
    env["LESS"] = "-FRX"

    return env


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
) -> CommandResult:
    display_command = shlex.join(command)
    print(f"\n$ {display_command}", flush=True)

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env or process_environment(),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )

        if completed.stdout:
            print(completed.stdout, end="", flush=True)

        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr, flush=True)

        return CommandResult(
            command=display_command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return CommandResult(
            command=display_command,
            return_code=124,
            stdout=stdout,
            stderr=f"{stderr}\nCommand timed out.",
        )


def run_shell_command(
    command: str,
    *,
    cwd: Path,
    timeout_seconds: int,
) -> CommandResult:
    # Verification commands come from your own local config.json.
    return run_command(
        ["/bin/zsh", "-lc", command],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
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


def git_status(project_root: Path) -> str:
    result = run_command(
        ["git", "--no-pager", "status", "--short"],
        cwd=project_root,
        timeout_seconds=30,
    )
    return result.stdout.strip()


def changed_files(project_root: Path) -> list[str]:
    result = run_command(
        ["git", "--no-pager", "status", "--porcelain"],
        cwd=project_root,
        timeout_seconds=30,
    )

    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        # Porcelain format: XY<space>path
        path = line[3:].strip()

        # Renames are represented as "old -> new".
        if " -> " in path:
            path = path.split(" -> ", 1)[1]

        files.append(path)

    return sorted(set(files))


def git_review_bundle(project_root: Path, max_chars: int = 60_000) -> str:
    tracked_diff = run_command(
        [
            "git",
            "--no-pager",
            "diff",
            "--no-ext-diff",
            "--unified=40",
            "--",
        ],
        cwd=project_root,
        timeout_seconds=60,
    ).stdout

    untracked = run_command(
        [
            "git",
            "--no-pager",
            "ls-files",
            "--others",
            "--exclude-standard",
        ],
        cwd=project_root,
        timeout_seconds=30,
    ).stdout.splitlines()

    sections = [tracked_diff]

    for relative_name in untracked:
        path = project_root / relative_name
        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            sections.append(
                f"\n--- UNTRACKED BINARY/UNREADABLE FILE: {relative_name} ---\n"
            )
            continue

        sections.append(
            f"\n--- UNTRACKED FILE: {relative_name} ---\n"
            f"{content[:20_000]}"
        )

    return "\n".join(sections)[-max_chars:]


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


def git_checkpoint(project_root: Path) -> str:
    """Return the current HEAD commit as a checkpoint."""

    result = run_command(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        timeout_seconds=30,
    )

    if not result.passed:
        raise RuntimeError(
            "Could not determine the current Git commit."
        )

    checkpoint = result.stdout.strip()

    if not checkpoint:
        raise RuntimeError(
            "Git returned an empty checkpoint commit."
        )

    return checkpoint


def git_restore_checkpoint(
    project_root: Path,
    checkpoint_commit: str,
) -> None:
    """Restore the working tree to a checkpoint commit."""

    result = run_command(
        ["git", "reset", "--hard", checkpoint_commit],
        cwd=project_root,
        timeout_seconds=60,
    )

    if not result.passed:
        raise RuntimeError(
            f"Could not restore Git checkpoint {checkpoint_commit}."
        )

    clean_result = run_command(
        ["git", "clean", "-fd"],
        cwd=project_root,
        timeout_seconds=60,
    )

    if not clean_result.passed:
        raise RuntimeError(
            "Could not remove files created after the checkpoint."
        )


def git_get_changes_since_commit(project_root: Path, commit_hash: str) -> list[str]:
    """Get all changed files since a specific commit."""
    result = run_command(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
        cwd=project_root,
        timeout_seconds=30,
    )
    
    if not result.passed:
        return []
        
    return sorted(set(line.strip() for line in result.stdout.splitlines() if line.strip()))


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
Do not add dependencies unless the current block explicitly requires it.
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

    # Include both existing and planned new files.
    for filename in block.get("files", []):
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
- Use only the supplied changes and verification output as evidence.
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

PROJECT CHANGES:

{diff}
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Nightshift against a Git repository."
    )
    parser.add_argument(
        "project",
        nargs="?",
        default=".",
        help="Path to the target Git repository. Defaults to current directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project).expanduser().resolve()

    if not (project_root / ".git").exists():
        print(
            f"ERROR: {project_root} is not a Git repository.",
            file=sys.stderr,
        )
        return 1

    if not CONFIG_PATH.exists():
        print(f"ERROR: Missing {CONFIG_PATH}", file=sys.stderr)
        return 1

    if not TASK_PATH.exists():
        print(f"ERROR: Missing {TASK_PATH}", file=sys.stderr)
        return 1

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    config = load_json(CONFIG_PATH)
    task = TASK_PATH.read_text(encoding="utf-8")

    if STATE_PATH.exists():
        state = load_json(STATE_PATH)
    else:
        state = {
            "status": "running",
            "project_root": str(project_root),
            "started_at": time.time(),
            "completed_blocks": [],
            "failed_blocks": [],
        }
        save_json(STATE_PATH, state)

    initial_status = git_status(project_root)
    if initial_status:
        print(
            "\nERROR: Target repository is not clean.\n"
            "Commit or stash existing work.\n\n"
            f"{initial_status}",
            file=sys.stderr,
        )
        return 1

    max_blocks = int(config.get("max_blocks", 8))
    max_attempts = int(config.get("max_attempts_per_block", 3))
    model = config["model"]

    # Create a checkpoint before starting
    try:
        initial_checkpoint = git_checkpoint(project_root)
    except RuntimeError as e:
        print(f"ERROR: Could not create initial checkpoint: {e}", file=sys.stderr)
        return 1

    for block_number in range(1, max_blocks + 1):
        plan = create_next_block(
            model=model,
            task=task,
            state=state,
            project_snapshot=git_status(project_root) or "Working tree is clean.",
        )

        if plan["complete"]:
            state["status"] = "completed"
            state["completion_reason"] = plan["reason"]
            state["finished_at"] = time.time()
            save_json(STATE_PATH, state)
            print("\nAll planned work is complete.")
            return 0

        block = plan["block"]
        if not isinstance(block, dict):
            raise RuntimeError("Planner returned complete=false but no block.")

        block_id = block["id"]
        previous_review: dict[str, Any] | None = None

        print(
            f"\n=== Block {block_number}: "
            f"{block_id} — {block['title']} ===",
            flush=True,
        )

        block_approved = False

        # Create a checkpoint for this block
        try:
            block_checkpoint = git_checkpoint(project_root)
        except RuntimeError as e:
            print(f"ERROR: Could not create block checkpoint: {e}", file=sys.stderr)
            return 1

        for attempt in range(1, max_attempts + 1):
            before_files = set(changed_files(project_root))

            prompt = build_aider_prompt(
                task=task,
                block=block,
                attempt=attempt,
                previous_review=previous_review,
            )

            aider_result = run_aider(
                project_root=project_root,
                config=config,
                prompt=prompt,
                block=block,
            )

            files = changed_files(project_root)
            newly_changed = sorted(set(files) - before_files)

            protected_violations = detect_protected_changes(
                files,
                config.get("protected_paths", []),
            )

            verification = run_verification(
                project_root=project_root,
                config=config,
            )
            
            # Get the diff for just this block
            block_diff = git_review_bundle(project_root)
            
            # Get only changes introduced by this specific block
            block_local_changes = git_get_changes_since_commit(project_root, block_checkpoint)

            review = review_block(
                model=model,
                task=task,
                block=block,
                diff=block_diff,
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

            approved = deterministic_pass and bool(review["approved"])

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
                "block_local_changes": block_local_changes,
            }

            write_report(block_id, attempt, report)

            if approved:
                state["completed_blocks"].append(
                    {
                        "block": block,
                        "attempts": attempt,
                        "changed_files": files,
                        "review": review,
                    }
                )
                save_json(STATE_PATH, state)

                print(f"\nBlock {block_id} approved.", flush=True)
                block_approved = True
                break

            previous_review = review
            print(
                f"\nBlock {block_id} rejected. "
                f"Attempt {attempt} of {max_attempts}.",
                flush=True,
            )
            
            # Restore to the block checkpoint if this attempt failed
            try:
                git_restore_checkpoint(project_root, block_checkpoint)
            except RuntimeError as e:
                print(f"WARNING: Could not restore block checkpoint: {e}", file=sys.stderr)

        # If all attempts for this block failed, restore to initial state
        if not block_approved:
            try:
                git_restore_checkpoint(project_root, initial_checkpoint)
            except RuntimeError as e:
                print(f"ERROR: Could not restore to initial state: {e}", file=sys.stderr)
                return 2
                
            state["status"] = "blocked"
            state["failed_blocks"].append(
                {
                    "block": block,
                    "last_review": previous_review,
                }
            )
            state["finished_at"] = time.time()
            save_json(STATE_PATH, state)

            print(
                f"\nStopped: block {block_id} could not be approved.",
                file=sys.stderr,
            )
            return 2

    state["status"] = "partial"
    state["reason"] = "Maximum number of blocks reached."
    state["finished_at"] = time.time()
    save_json(STATE_PATH, state)

    print("\nStopped after reaching the configured block limit.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
