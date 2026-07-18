
from pathlib import Path

from builder import BuilderTask, run_builder


PROMPT = """
Add unit tests for execute_backlog().

Requirements:
- Add tests only to test_orchestrator.py.
- Do not modify orchestrator.py.
- Verify that Planner.from_backlog() is called exactly once with the supplied backlog_file.
- Verify that execute_all_tasks() is called exactly once with:
  - the planner returned by Planner.from_backlog()
  - the supplied project_root
  - the supplied config
- Verify that execute_backlog() returns the tuple returned by execute_all_tasks() unchanged.
- Do not modify existing tests.
- Do not perform any refactoring.
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
