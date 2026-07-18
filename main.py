from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backlog import Backlog, Feature, Task, TaskStatus
from orchestrator import execute_next_task
from planner import Planner


PROMPT = """
Analyze the current Nightshift architecture and implement exactly one small,
high-value refactoring that improves separation of responsibilities without
changing external behavior.

Requirements:

- Select exactly one narrowly scoped refactoring.
- The Architect must create and validate an Architecture Contract before the
  Builder is invoked.
- The Builder must implement only the validated Architecture Contract.
- Preserve existing public APIs and behavior.
- Do not add dependencies.
- Do not perform unrelated cleanup.
- Add or update focused tests when needed.
- Run the complete test suite.
- Do not commit, push, merge, rebase, or reset Git history.
""".strip()


FILES = (
    Path("architect.py"),
    Path("contracts.py"),
    Path("planner.py"),
    Path("backlog.py"),
    Path("builder.py"),
    Path("review.py"),
    Path("orchestrator.py"),
    Path("orchestrator_runtime.py"),
    Path("autonomous_orchestrator.py"),
    Path("cycle_execution.py"),
    Path("git_tools.py"),
    Path("ollama_workflow.py"),
    Path("aider_workflow.py"),
    Path("test_architect.py"),
    Path("test_contracts.py"),
    Path("test_role_handoffs.py"),
)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise ValueError("config.json must contain a JSON object")

    return value


def create_backlog() -> Backlog:
    now = datetime.now(timezone.utc)

    task = Task(
        id="nightshift-self-refactor-001",
        title="Improve Nightshift architecture",
        prompt=PROMPT,
        files=FILES,
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )

    feature = Feature(
        id="nightshift-self-development",
        title="Nightshift self-development",
        tasks=(task,),
    )

    return Backlog(features=(feature,))


def main() -> int:
    project_root = Path.cwd()
    config = load_config(project_root / "config.json")
    planner = Planner(create_backlog())

    result = execute_next_task(
        planner=planner,
        project_root=project_root,
        config=config,
    )

    if result is None:
        print("No task was available.")
        return 0

    approved = getattr(result, "approved", None)

    if approved is True:
        print("Nightshift cycle completed and was approved.")
        return 0

    if approved is False:
        print("Nightshift cycle completed but was not approved.")
        return 1

    review_result = getattr(result, "review_result", None)
    review_approved = getattr(review_result, "approved", None)

    if review_approved is True:
        print("Nightshift cycle completed and the review was approved.")
        return 0

    if review_approved is False:
        print("Nightshift cycle completed but the review was not approved.")
        return 1

    print("Nightshift cycle completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())