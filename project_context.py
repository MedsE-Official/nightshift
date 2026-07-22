"""Paths that describe a Nightshift-enabled project.

This module deliberately contains no file loading or validation logic.  It only
provides one place for locating the project-local Nightshift files.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectContext:
    """Locate the project-local Nightshift configuration files."""

    project_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", Path(self.project_root).resolve())

    @property
    def nightshift_root(self) -> Path:
        return self.project_root / ".nightshift"

    @property
    def project_file(self) -> Path:
        return self.nightshift_root / "project.json"

    @property
    def backlog_file(self) -> Path:
        return self.nightshift_root / "backlog.json"

    @property
    def knowledge_file(self) -> Path:
        return self.nightshift_root / "knowledge.json"

    @property
    def adr_file(self) -> Path:
        return self.nightshift_root / "adr.json"

    @property
    def prompts_file(self) -> Path:
        return self.nightshift_root / "prompts.json"

    def is_nightshift_project(self) -> bool:
        """Return whether the project contains the conventional control folder."""

        return self.nightshift_root.is_dir()
