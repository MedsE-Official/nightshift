from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class BuilderTask:
    prompt: str
    files: tuple[Path, ...]


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
    task: BuilderTask,
    project_root: Path,
    timeout_seconds: int = 900,
) -> BuilderResult:
    """Run one isolated Aider session for one micro-task."""

    resolved_project_root = project_root.expanduser().resolve()

    if not resolved_project_root.is_dir():
        raise ValueError(
            f"Project root does not exist: {resolved_project_root}"
        )

    if not task.prompt.strip():
        raise ValueError("Builder prompt must not be empty.")

    file_arguments: list[str] = []

    for file_path in task.files:
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
        "--edit-format",
        "diff",
        "--no-show-model-warnings",
        "--no-pretty",
        "--no-stream",
        "--yes-always",
        "--no-auto-commits",
        "--message",
        task.prompt,
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
