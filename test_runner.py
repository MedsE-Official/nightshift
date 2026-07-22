#!/usr/bin/env python3

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecutionResult:
    return_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def run_tests(
    *,
    project_root: Path | None = None,
    config: dict[str, Any] | None = None,
    run_test_command: bool = True,
) -> ExecutionResult:
    """Run the configured tests in the target repository.

    Calling without arguments preserves the original self-test behaviour used by
    older Nightshift callers and tests.
    """

    if project_root is None:
        root = Path.cwd()
        commands = (
            [
                [sys.executable, "-m", "py_compile", "orchestrator.py", "config.py"],
                [sys.executable, "-m", "unittest", "test_orchestrator.py"],
            ]
            if run_test_command
            else []
        )
    else:
        root = Path(project_root).expanduser().resolve()
        test_command = (config or {}).get("commands", {}).get("test")
        if not isinstance(test_command, str) or not test_command.strip():
            test_command = f"{shlex.quote(sys.executable)} -m pytest -q"
        commands = [shlex.split(test_command)] if run_test_command else []

    try:
        for command in commands:
            completed = _run(command, cwd=root)
            if completed.returncode != 0:
                return ExecutionResult(
                    return_code=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )

        diff_check = _run(["git", "--no-pager", "diff", "--check"], cwd=root)
        if diff_check.returncode != 0:
            return ExecutionResult(
                return_code=diff_check.returncode,
                stdout=diff_check.stdout,
                stderr=diff_check.stderr,
            )

        stdout = "" if run_test_command else "Tests skipped by task configuration."
        return ExecutionResult(return_code=0, stdout=stdout, stderr="")
    except Exception as exc:
        return ExecutionResult(return_code=1, stdout="", stderr=str(exc))


if __name__ == "__main__":
    result = run_tests()
    raise SystemExit(0 if result.passed else 1)
