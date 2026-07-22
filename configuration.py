"""Single gateway for validated project-local Nightshift configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from knowledge_base import KnowledgeBase
from project_context import ProjectContext
from project_loader import ProjectData, ProjectLoader
from prompt_catalog import PromptCatalog


@dataclass(frozen=True)
class Configuration:
    """Validated project control data loaded through one public entry point."""

    context: ProjectContext
    data: ProjectData
    prompt_catalog: PromptCatalog
    project_knowledge: KnowledgeBase

    @classmethod
    def load(
        cls,
        project_root: Path,
        *,
        schema_root: Path | None = None,
    ) -> "Configuration":
        context = ProjectContext(project_root)
        data = ProjectLoader(context, schema_root=schema_root).load()
        return cls(
            context=context,
            data=data,
            prompt_catalog=PromptCatalog.from_dict(data.prompts),
            project_knowledge=KnowledgeBase.from_dict(data.knowledge),
        )

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

    @property
    def prompts(self) -> dict[str, Any]:
        return self.data.prompts

    def prompt(self, role: str) -> str:
        return self.prompt_catalog.get(role)

    def role_context(self, role: str) -> str:
        return (
            f"{self.prompt(role)}\n\n"
            f"PROJECT KNOWLEDGE:\n{self.project_knowledge.render(role=role)}"
        )
