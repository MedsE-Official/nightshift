from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bootstrap import bootstrap
from orchestrator import execute_next_task
from planner import Planner


def load_runtime_config(path: Path) -> dict[str, Any]:
    """Load framework runtime settings.

    Project control documents are loaded separately through Configuration.
    """

    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise ValueError("config.json must contain a JSON object")

    return value


def main() -> int:
    project_root = Path.cwd()
    configuration = bootstrap(project_root)
    runtime_config = load_runtime_config(project_root / "config.json")
    planner = Planner.from_configuration(configuration)

    result = execute_next_task(
        planner=planner,
        project_root=project_root,
        config=runtime_config,
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
