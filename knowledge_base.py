"""Project knowledge loaded from JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    title: str
    content: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeBase:
    entries: tuple[KnowledgeEntry, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeBase":
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError("'entries' must be an array")

        entries: list[KnowledgeEntry] = []
        for index, raw in enumerate(raw_entries):
            if not isinstance(raw, dict):
                raise ValueError(f"Knowledge entry at index {index} must be an object")
            tags = raw.get("tags", [])
            if not isinstance(tags, list) or not all(
                isinstance(tag, str) for tag in tags
            ):
                raise ValueError(
                    f"Knowledge entry at index {index} tags must be an array of strings"
                )
            entries.append(
                KnowledgeEntry(
                    id=str(raw["id"]),
                    title=str(raw["title"]),
                    content=str(raw["content"]),
                    tags=tuple(tags),
                )
            )
        return cls(entries=tuple(entries))

    def render(self, *, role: str | None = None) -> str:
        selected = tuple(
            entry
            for entry in self.entries
            if role is None or not entry.tags or role in entry.tags
        )
        if not selected:
            return "No project-specific knowledge is configured."

        return "\n\n".join(
            f"## {entry.title}\n{entry.content}" for entry in selected
        )
