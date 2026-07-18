
from pathlib import Path

from builder import BuilderTask, run_builder


PROMPT = """
Task 3.0.2 – Execute all tasks from Planner

Goal

Add a small orchestration helper that executes Planner tasks sequentially until no tasks remain.

Modify only:

- orchestrator.py
- test_orchestrator.py

Requirements

1. Add this function to orchestrator.py:

    execute_all_tasks(
        *,
        planner: Planner,
        project_root: Path,
        config: dict[str, Any],
    ) -> tuple[CycleResult, ...]

2. execute_all_tasks() must repeatedly call:

    execute_next_task(
        planner=planner,
        project_root=project_root,
        config=config,
    )

3. When execute_next_task() returns None, execution must stop.

4. Return all produced CycleResult objects as a tuple, preserving execution order.

5. If the Planner contains no tasks, return an empty tuple.

6. Do not catch or suppress exceptions from execute_next_task().

7. Add focused unit tests for:

    - an empty Planner
    - multiple CycleResult objects returned in order
    - stopping immediately after execute_next_task() returns None

8. Do not modify the existing main() function.
9. Do not remove or move existing orchestration code.
10. Do not modify Planner, Builder, Review, or prompts.
11. Do not perform unrelated cleanup.
12. Do not commit or push.

Run:

    pytest -q
""".strip()

FILES = [
    Path("orchestrator.py"),
    Path("test_orchestrator.py"),
]


def main() -> int:

    task = BuilderTask(
        prompt=PROMPT,
        files=tuple(FILES),
    )

    result = run_builder(
        task=task,
        project_root=Path.cwd(),
        timeout_seconds=15 * 60,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    return result.return_code


if __name__ == "__main__":
    raise SystemExit(main())
