
from pathlib import Path

from builder import BuilderTask, run_builder


PROMPT = """
Change only test_builder.py.

Replace the placeholder test for run_builder() with a real signature test using inspect.signature.

Assert that:
- "task" is present;
- "prompt" is absent;
- "files" is absent.

Do not modify production code or any other test.
""".strip()

FILES = [
    Path("test_builder.py"),
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
