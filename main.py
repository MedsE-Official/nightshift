from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backlog import Backlog, Feature, Task, TaskStatus
from orchestrator import execute_next_task
from planner import Planner


PROMPT = """
The fix prevents the crash but hides all API Guard failures.

Do not suppress all exceptions.

Instead:

- identify why before.py and after.py do not exist
- create the snapshots before API Guard executes
- or explicitly skip only when snapshots are unavailable

Preserve API Guard's ability to detect genuine API regressions.

Add a regression test that reproduces the original FileNotFoundError.
""".strip()


FILES = (
    Path("api_guard.py"),
    Path("review.py"),
    Path("test_api_guard.py"),
    Path("test_review.py"),
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