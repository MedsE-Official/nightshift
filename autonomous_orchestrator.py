from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from aider_workflow import build_aider_prompt, run_aider, run_verification, write_report
from architect import create_architecture_contract
from contracts import contract_change_violations
from git_tools import (changed_files, detect_protected_changes, git_checkpoint, git_get_changes_since_commit, git_restore_checkpoint, git_review_bundle, git_status)
from ollama_workflow import create_next_block, review_block
from orchestrator_runtime import load_json, save_json
from preflight import run_preflight

NIGHTSHIFT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = NIGHTSHIFT_ROOT / "config.json"
TASK_PATH = NIGHTSHIFT_ROOT / "task.md"
STATE_DIR = NIGHTSHIFT_ROOT / "state"
REPORT_DIR = NIGHTSHIFT_ROOT / "reports"
STATE_PATH = STATE_DIR / "progress.json"
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

    # Run preflight checks
    preflight_result = run_preflight(project_root)
    if not preflight_result.passed:
        print("Preflight checks failed:")
        for error in preflight_result.errors:
            print(f"  - {error}")
        return 1

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

        architecture_contract = create_architecture_contract(
            model=model,
            task=task,
            block=block,
            project_snapshot=git_status(project_root) or "Working tree is clean.",
            config=config,
        )

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
                architecture_contract=architecture_contract,
            )

            aider_result = run_aider(
                project_root=project_root,
                config=config,
                prompt=prompt,
                block=block,
                architecture_contract=architecture_contract,
            )

            files = changed_files(project_root)
            newly_changed = sorted(set(files) - before_files)

            protected_violations = detect_protected_changes(
                files,
                config.get("protected_paths", []),
            )
            architecture_violations = contract_change_violations(
                files,
                architecture_contract,
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
                architecture_contract=architecture_contract,
                contract_violations=architecture_violations,
            )

            deterministic_pass = (
                aider_result.passed
                and not protected_violations
                and not architecture_violations
                and all(
                    result["passed"]
                    for result in verification.values()
                )
            )

            approved = deterministic_pass and bool(review["approved"])

            report = {
                "block": block,
                "architecture_contract": architecture_contract.to_dict(),
                "attempt": attempt,
                "aider_return_code": aider_result.return_code,
                "changed_files": files,
                "newly_changed_files": newly_changed,
                "protected_violations": protected_violations,
                "architecture_violations": architecture_violations,
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
                        "architecture_contract": architecture_contract.to_dict(),
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
                    "architecture_contract": architecture_contract.to_dict(),
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
