from pathlib import Path
from builder import run_builder, BuilderResult

def main() -> int:
    project_root = Path.cwd()

    prompt = """
Goal

Add one isolated helper that detects removed public symbols.

Files available to you

- api_guard.py
- test_api_guard.py

Files allowed to modify

- api_guard.py
- test_api_guard.py

Requirements

- Add:
  detect_removed_public_symbols(
      before_source: str,
      after_source: str,
  ) -> set[str]

- Reuse extract_public_symbols() and compare_symbol_sets().
- Return only removed symbols.
- Add focused tests.

Restrictions

- Do not modify existing functions.
- Do not modify existing tests.
- Only append new code.
- Do not refactor unrelated code.
- Do not commit or push.

Verification

python3 -m pytest -q
python3 -m py_compile api_guard.py
git --no-pager diff --check
""".strip()

    result = run_builder(
        prompt=prompt,
        files=[
            Path("api_guard.py"),
            Path("test_api_guard.py"),
        ],
        project_root=project_root,
        timeout_seconds=15 * 60,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    return result.return_code


if __name__ == "__main__":
    raise SystemExit(main())
