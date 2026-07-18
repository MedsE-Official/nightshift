
from pathlib import Path

from builder import BuilderTask, run_builder


PROMPT = """
Refactor Planner to consume a Backlog instance instead of reading directly from a file.

Requirements:
- Modify only planner.py and test_planner.py.
- Planner shall accept a Backlog object.
- Do not change the Backlog model.
- Preserve existing planner behavior.
- Update existing tests as needed.
- Do not modify orchestrator.py or other files.
- Do not add new functionality beyond consuming Backlog.
""".strip()

FILES = [
    Path("planner.py"),
    Path("test_planner.py"),
    Path("backlog.py"),
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
