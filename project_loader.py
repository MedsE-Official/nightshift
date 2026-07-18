"""Load and validate project-local Nightshift control data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "ProjectLoader requires the 'jsonschema' package. "
        "Install project dependencies with: python -m pip install -r requirements.txt"
    ) from exc

from project_context import ProjectContext


class ProjectLoadError(RuntimeError):
    """Raised when project control data cannot be loaded or validated."""


@dataclass(frozen=True)
class ProjectData:
    """The four project-local JSON master documents."""

    project: dict[str, Any]
    backlog: dict[str, Any]
    knowledge: dict[str, Any]
    adr: dict[str, Any]


class ProjectLoader:
    """Load conventional project files and validate them against framework schemas."""

    _FILES = {
        "project": ("project_file", "project.schema.json"),
        "backlog": ("backlog_file", "backlog.schema.json"),
        "knowledge": ("knowledge_file", "knowledge.schema.json"),
        "adr": ("adr_file", "adr.schema.json"),
    }

    def __init__(
        self,
        context: ProjectContext,
        schema_root: Path | None = None,
    ) -> None:
        self.context = context
        self.schema_root = (
            Path(schema_root).resolve()
            if schema_root is not None
            else Path(__file__).resolve().parent / "schema"
        )

    def load(self) -> ProjectData:
        """Load and validate all project-local JSON master documents."""

        loaded = {
            name: self._load_document(
                path=getattr(self.context, path_attribute),
                schema_path=self.schema_root / schema_filename,
            )
            for name, (path_attribute, schema_filename) in self._FILES.items()
        }
        return ProjectData(**loaded)

    def _load_document(self, path: Path, schema_path: Path) -> dict[str, Any]:
        document = self._read_json(path, kind="project document")
        schema = self._read_json(schema_path, kind="JSON schema")

        try:
            Draft202012Validator(schema).validate(document)
        except ValidationError as exc:
            location = ".".join(str(part) for part in exc.absolute_path) or "<root>"
            raise ProjectLoadError(
                f"Invalid project document {path}: {location}: {exc.message}"
            ) from exc

        return document

    @staticmethod
    def _read_json(path: Path, *, kind: str) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as file:
                value = json.load(file)
        except FileNotFoundError as exc:
            raise ProjectLoadError(f"Missing {kind}: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ProjectLoadError(
                f"Invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: "
                f"{exc.msg}"
            ) from exc

        if not isinstance(value, dict):
            raise ProjectLoadError(f"Expected JSON object in {path}")
        return value
