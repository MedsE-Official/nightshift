#!/usr/bin/env python3

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    return_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0


def run_tests() -> ExecutionResult:
    """Run all tests for the orchestrator."""
    print("Running orchestrator tests...")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "py_compile",
                "orchestrator.py",
                "config.py",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Compilation failed:")
            print(result.stderr)
            return ExecutionResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        print("✓ Compilation successful")

        result = subprocess.run(
            [sys.executable, "-m", "unittest", "test_orchestrator.py"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Unit tests failed:")
            print(result.stderr)
            return ExecutionResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        print("✓ Unit tests passed")

        result = subprocess.run(
            ["git", "--no-pager", "diff", "--check"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Git diff check failed:")
            print(result.stdout)
            return ExecutionResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        print("\nAll checks passed!")
        return ExecutionResult(return_code=0, stdout="", stderr="")

    except Exception as exc:
        print(f"Error running tests: {exc}")
        return ExecutionResult(return_code=1, stdout="", stderr=str(exc))


if __name__ == "__main__":
    result = run_tests()
    raise SystemExit(0 if result.passed else 1)