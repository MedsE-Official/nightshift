from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

TASK = """
Implement a new function in src/calculator.py:

    divide(a: float, b: float) -> float

Requirements:
- Return a / b.
- Raise ValueError with the exact message "Cannot divide by zero"
  when b is zero.
- Preserve the existing add function.
- Add tests to tests/test_calculator.py.
- Test normal division.
- Test division by zero and verify the exact error message.
- Do not modify any other files.
- Do not commit or push.
"""


def run(command: list[str], *, env: dict[str, str] | None = None) -> int:
    print(f"\n$ {' '.join(command)}\n", flush=True)

    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
    )

    return completed.returncode


def main() -> int:
    env = os.environ.copy()
    env["OPENAI_API_BASE"] = "http://localhost:11434/v1"
    env["OPENAI_API_KEY"] = "ollama"
    env["PAGER"] = "cat"
    env["GIT_PAGER"] = "cat"
    env["AIDER_PAGER"] = "cat"


    aider_command = [
        "aider",
        "--model",
        "openai/qwen3-coder:latest",
        "--no-show-model-warnings",
        "--no-pretty",
        "--yes-always",
        "--no-auto-commits",
        "--no-stream",
        "--test-cmd",
        "python3 -m pytest -q",
        "--auto-test",
        "--message",
        TASK,
        "src/calculator.py",
        "tests/test_calculator.py",
    ]

    aider_exit_code = run(aider_command, env=env)

    if aider_exit_code != 0:
        print(
            f"\nFAILED: Aider exited with code {aider_exit_code}.",
            file=sys.stderr,
        )
        return 1

    test_exit_code = run([
        "python3",
        "-m",
        "pytest",
        "-q",
    ])

    if test_exit_code != 0:
        print(
            "\nFAILED: Independent test execution failed.",
            file=sys.stderr,
        )
        return 2

    diff_exit_code = run([
        "git",
        "--no-pager",
        "diff",
        "--check",
    ])

    if diff_exit_code != 0:
        print(
            "\nFAILED: Git found whitespace or patch errors.",
            file=sys.stderr,
        )
        return 3

    print("\nSUCCESS: Aider completed the task and all checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
