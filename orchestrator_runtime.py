from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import settings
@dataclass
class CommandResult:
    command: str
    return_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0

    def combined_output(self, max_chars: int = 20_000) -> str:
        output = f"{self.stdout}\n{self.stderr}".strip()
        return output[-max_chars:]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=False)

    temporary.replace(path)


def process_environment() -> dict[str, str]:
    env = os.environ.copy()

    # Aider talks to Ollama through Ollama's OpenAI-compatible endpoint.
    env.setdefault("OPENAI_API_BASE", settings.openai_api_base)
    env.setdefault("OPENAI_API_KEY", "ollama")

    # Prevent pagers and alternate terminal screens during unattended runs.
    env["PAGER"] = "cat"
    env["GIT_PAGER"] = "cat"
    env["LESS"] = "-FRX"

    return env


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
) -> CommandResult:
    display_command = shlex.join(command)
    print(f"\n$ {display_command}", flush=True)

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env or process_environment(),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )

        if completed.stdout:
            print(completed.stdout, end="", flush=True)

        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr, flush=True)

        return CommandResult(
            command=display_command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return CommandResult(
            command=display_command,
            return_code=124,
            stdout=stdout,
            stderr=f"{stderr}\nCommand timed out.",
        )


def run_shell_command(
    command: str,
    *,
    cwd: Path,
    timeout_seconds: int,
) -> CommandResult:
    # Verification commands come from your own local config.json.
    return run_command(
        ["/bin/zsh", "-lc", command],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )
