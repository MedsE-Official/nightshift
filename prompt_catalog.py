"""Validated project-local prompt catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PromptCatalog:
    """Role prompts loaded from the project JSON source of truth."""

    prompts: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptCatalog":
        prompts = data.get("prompts")
        if not isinstance(prompts, dict):
            raise ValueError("'prompts' must be an object")

        invalid = [
            name
            for name, value in prompts.items()
            if not isinstance(name, str)
            or not name.strip()
            or not isinstance(value, str)
            or not value.strip()
        ]
        if invalid:
            raise ValueError("Prompt names and prompt values must be non-empty strings")

        return cls(prompts=dict(prompts))

    def get(self, role: str) -> str:
        try:
            return self.prompts[role]
        except KeyError as exc:
            raise KeyError(f"No prompt configured for role: {role}") from exc
