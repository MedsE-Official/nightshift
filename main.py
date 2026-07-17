
from pathlib import Path

from builder import BuilderTask, run_builder


PROMPT = """
Task 2.5.1 – Introduce execute_cycle()

Implement a minimal execute_cycle() function.

Modify only:

- orchestrator.py
- test_orchestrator.py

Requirements:

- Add execute_cycle().
- Accept:
    planner,
    project_root,
    config.
- Ask the planner for exactly one BuilderTask.
- If no BuilderTask exists, return None.
- Call run_builder() exactly once.
- Call run_tests() exactly once.
- Call run_review() exactly once.
- Return a CycleResult containing:
    builder_result,
    test_result,
    review_result.

Constraints:

- Do not modify main().
- Do not move existing logic.
- Do not implement retries.
- Do not update state.
- Do not create reports.
- Do not capture Git diffs.
- Do not perform checkpointing.
- Do not change Builder, Review or TestRunner APIs.
- Add only the tests required for execute_cycle().
- Preserve all existing behaviour.
- Do not commit or push.
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
