"""Single gateway for validated project-local Nightshift configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_context import ProjectContext
from project_loader import ProjectData, ProjectLoader


@dataclass(frozen=True)
class Configuration:
    """Validated project control data loaded through one public entry point."""

    context: ProjectContext
    data: ProjectData

    @classmethod
    def load(
        cls,
        project_root: Path,
        *,
        schema_root: Path | None = None,
    ) -> "Configuration":
        context = ProjectContext(project_root)
        data = ProjectLoader(context, schema_root=schema_root).load()
        return cls(context=context, data=data)

    @property
    def project(self) -> dict[str, Any]:
        return self.data.project

    @property
    def backlog(self) -> dict[str, Any]:
        return self.data.backlog

    @property
    def knowledge(self) -> dict[str, Any]:
        return self.data.knowledge

    @property
    def adr(self) -> dict[str, Any]:
        return self.data.adr
