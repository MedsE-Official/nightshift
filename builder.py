from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class BuilderResult:
    return_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0


def build_environment() -> dict[str, str]:
    """Create the environment used by Aider."""

    environment = os.environ.copy()

    environment["OPENAI_API_BASE"] = "http://localhost:11434/v1"
    environment["OPENAI_API_KEY"] = "ollama"

    # Prevent Git or other tools from opening pagers.
    environment["PAGER"] = "cat"
    environment["GIT_PAGER"] = "cat"
    environment["LESS"] = "-FRX"

    return environment


def run_builder(
    *,
    prompt: str,
    files: Sequence[Path],
    project_root: Path,
    timeout_seconds: int = 900,
) -> BuilderResult:
    """Run one isolated Aider session for one micro-task."""

    resolved_project_root = project_root.expanduser().resolve()

    if not resolved_project_root.is_dir():
        raise ValueError(
            f"Project root does not exist: {resolved_project_root}"
        )

    if not prompt.strip():
        raise ValueError("Builder prompt must not be empty.")

    file_arguments: list[str] = []

    for file_path in files:
        absolute_path = (
            file_path
            if file_path.is_absolute()
            else resolved_project_root / file_path
        ).resolve()

        try:
            relative_path = absolute_path.relative_to(resolved_project_root)
        except ValueError as error:
            raise ValueError(
                f"Builder file must be inside project root: {absolute_path}"
            ) from error

        file_arguments.append(str(relative_path))

    command = [
        "aider",
        "--model",
        "openai/qwen3-coder:latest",
        "--no-show-model-warnings",
        "--no-pretty",
        "--no-stream",
        "--yes-always",
        "--no-auto-commits",
        "--message",
        prompt,
        *file_arguments,
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=resolved_project_root,
            env=build_environment(),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Aider executable was not found."
        ) from error
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return BuilderResult(
            return_code=124,
            stdout=stdout,
            stderr=f"{stderr}\nBuilder timed out.".strip(),
        )

    return BuilderResult(
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


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
