
from pathlib import Path

from builder import BuilderTask, run_builder


PROMPT = """
Task 2.5.1 – Design the orchestration refactor

Inspect only:

- orchestrator.py
- planner.py
- builder.py
- test_runner.py
- review.py

Do not modify any files.

Nightshift currently contains two orchestration flows:

1. The existing orchestration inside main().
2. The new execute_cycle() orchestration.

Design how these should be unified so execute_cycle() becomes the single owner of one development iteration.

For each responsibility, determine its owner:

- selecting the next BuilderTask
- running Builder
- running tests
- capturing the Git diff
- running Review
- updating state
- writing reports
- retry handling
- deciding whether another cycle should start

Produce:

1. A responsibility matrix.
2. The proposed execute_cycle() signature.
3. The minimal implementation plan.
4. A migration plan consisting of microtasks where each implementation task modifies at most two files.
5. Any risks or unresolved architectural decisions.

Do not implement anything.
Do not refactor.
Do not change public APIs.
Do not commit or push.
""".strip()

FILES = [
    Path("orchestrator.py"),
    Path("planner.py"),
    Path("builder.py"),
    Path("test_runner.py"),
    Path("review.py"),
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
