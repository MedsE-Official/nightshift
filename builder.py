from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence


if TYPE_CHECKING:
    from configuration import Configuration


@dataclass(frozen=True)
class BuilderTask:
    prompt: str
    files: tuple[Path, ...]
    run_tests: bool = True

    @property
    def review_block(self) -> dict[str, object]:
        return {
            "prompt": self.prompt,
            "files": [str(path) for path in self.files],
        }

@dataclass(frozen=True)
class BuilderResult:
    return_code: int
    stdout: str
    stderr: str
    has_changes: bool
    status: BuilderStatus

    @property
    def passed(self) -> bool:
        return self.return_code == 0 and self.has_changes




def builder_task_has_changes(
    *,
    task: BuilderTask,
    project_root: Path,
) -> bool:
    """Detect whether any file belonging to a BuilderTask has changed in Git."""
    
    resolved_project_root = project_root.expanduser().resolve()
    
    # Prepare the list of files for git status
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
    
    # Run git status --porcelain on the task files
    command = ["git", "status", "--porcelain", "--"] + file_arguments
    
    try:
        completed = subprocess.run(
            command,
            cwd=resolved_project_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        # Git is not available
        return False
    
    # Return True if there's any output (changed or untracked files)
    return bool(completed.stdout.strip())


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


class BuilderStatus(Enum):
    SUCCESS = "success"
    NO_CHANGES = "no_changes"
    FAILED = "failed"
    TIMEOUT = "timeout"


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
            has_changes=False,
            status=BuilderStatus.TIMEOUT,
        )

    # Determine if files have changed
    has_changes = builder_task_has_changes(
        task=task,
        project_root=resolved_project_root,
    )
    
    # Determine the status based on return code and changes
    if completed.returncode == 0:
        status = BuilderStatus.SUCCESS if has_changes else BuilderStatus.NO_CHANGES
    else:
        status = BuilderStatus.FAILED
    
    return BuilderResult(
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        has_changes=has_changes,
        status=status,
    )


@dataclass(frozen=True)
class Builder:
    """Configuration-aware Builder entry point."""

    configuration: "Configuration"

    @classmethod
    def from_configuration(cls, configuration: "Configuration") -> "Builder":
        return cls(configuration=configuration)

    def run(
        self,
        *,
        task: BuilderTask,
        runtime_config: dict[str, Any],
    ) -> BuilderResult:
        guidance = self.configuration.role_context("builder")
        effective_task = BuilderTask(
            prompt=f"{guidance}\n\nCURRENT TASK:\n{task.prompt}",
            files=task.files,
            run_tests=task.run_tests,
        )
        return run_builder(
            task=effective_task,
            project_root=self.configuration.context.project_root,
            timeout_seconds=int(
                runtime_config.get("timeout_minutes_per_aider_run", 15)
            ) * 60,
        )
