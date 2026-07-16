
from pathlib import Path

from builder import run_builder


PROMPT = """
Task 1.2.1g.1 – Fix run_review tests only

Files allowed to modify

- test_review.py

Requirements

- Do not modify review.py.
- Both tests must call run_review() directly.
- Create real before.py and after.py files in a temporary project directory.
- Pass minimal config, block and diff arguments.
- Success test must assert:
  - no "errors" key exists;
  - api_guard_result.passed is True.
- Failure test must assert:
  - exactly one error exists;
  - the error contains "func2";
  - api_guard_result.passed is False.
- Remove conditional assertions that allow missing errors.
- Do not modify existing _run_api_guard tests.
- Do not refactor unrelated code.

Verification

python3 -m pytest -q
git --no-pager diff --check
""".strip()

FILES = [
    Path("test_review.py"),
]


def main() -> int:
    result = run_builder(
        prompt=PROMPT,
        files=FILES,
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
