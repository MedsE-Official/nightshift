"""Project-level Architect planning for human-written product requirements."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from configuration import Configuration
from ollama_workflow import ollama_structured


ARCHITECT_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "features"],
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "tasks"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "title": {"type": "string", "minLength": 1},
                    "tasks": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["id", "title", "prompt", "files"],
                            "properties": {
                                "id": {"type": "string", "minLength": 1},
                                "title": {"type": "string", "minLength": 1},
                                "prompt": {"type": "string", "minLength": 1},
                                "files": {
                                    "type": "array",
                                    "items": {"type": "string", "minLength": 1},
                                    "uniqueItems": True,
                                },
                                "run_tests": {"type": "boolean", "default": True},
                            },
                        },
                    },
                },
            },
        },
    },
}


@dataclass(frozen=True)
class SourceTreeSnapshot:
    files: tuple[str, ...]
    excerpts: dict[str, str]
    truncated: bool = False

    def render(self) -> str:
        lines = ["FILES:", *self.files]
        if self.truncated:
            lines.append("[file list truncated]")
        if self.excerpts:
            lines.append("\nSOURCE EXCERPTS:")
            for path, content in self.excerpts.items():
                lines.append(f"\n--- {path} ---\n{content}")
        return "\n".join(lines)


@dataclass(frozen=True)
class ProjectAnalysis:
    project: dict[str, Any]
    backlog: dict[str, Any]
    knowledge: dict[str, Any]
    source_tree: SourceTreeSnapshot

    def render(self) -> str:
        return "\n\n".join(
            [
                "PROJECT:\n" + json.dumps(self.project, indent=2, ensure_ascii=False),
                "CURRENT BACKLOG:\n"
                + json.dumps(self.backlog, indent=2, ensure_ascii=False),
                "PROJECT KNOWLEDGE:\n"
                + json.dumps(self.knowledge, indent=2, ensure_ascii=False),
                "SOURCE TREE:\n" + self.source_tree.render(),
            ]
        )


class KnowledgeLoader:
    """Expose validated project knowledge for project-level architecture."""

    @staticmethod
    def load(configuration: Configuration) -> dict[str, Any]:
        return configuration.knowledge


class SourceTreeAnalyzer:
    """Create a bounded, deterministic snapshot of a target repository."""

    DEFAULT_EXCLUDED_DIRS = {
        ".git",
        ".nightshift",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
    }
    DEFAULT_TEXT_SUFFIXES = {
        ".py",
        ".toml",
        ".json",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
    }

    def __init__(
        self,
        *,
        max_files: int = 200,
        max_excerpt_files: int = 30,
        max_chars_per_file: int = 4000,
    ) -> None:
        self.max_files = max_files
        self.max_excerpt_files = max_excerpt_files
        self.max_chars_per_file = max_chars_per_file

    def analyze(self, project_root: Path) -> SourceTreeSnapshot:
        root = Path(project_root).resolve()
        paths: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in self.DEFAULT_EXCLUDED_DIRS for part in relative.parts):
                continue
            paths.append(relative)

        paths.sort(key=lambda item: item.as_posix())
        truncated = len(paths) > self.max_files
        selected = paths[: self.max_files]
        excerpts: dict[str, str] = {}

        for relative in selected:
            if len(excerpts) >= self.max_excerpt_files:
                break
            if relative.suffix.lower() not in self.DEFAULT_TEXT_SUFFIXES:
                continue
            absolute = root / relative
            try:
                content = absolute.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            excerpts[relative.as_posix()] = content[: self.max_chars_per_file]

        return SourceTreeSnapshot(
            files=tuple(path.as_posix() for path in selected),
            excerpts=excerpts,
            truncated=truncated,
        )


class ProjectAnalyzer:
    """Load validated control data and inspect the current source tree."""

    def __init__(self, source_analyzer: SourceTreeAnalyzer | None = None) -> None:
        self.source_analyzer = source_analyzer or SourceTreeAnalyzer()

    def analyze(self, configuration: Configuration) -> ProjectAnalysis:
        return ProjectAnalysis(
            project=configuration.project,
            backlog=configuration.backlog,
            knowledge=KnowledgeLoader.load(configuration),
            source_tree=self.source_analyzer.analyze(configuration.context.project_root),
        )


class ArchitectAgent:
    """Use a structured LLM response to translate requirements into backlog additions."""

    def __init__(
        self,
        *,
        model: str,
        structured_call: Callable[..., dict[str, Any]] = ollama_structured,
    ) -> None:
        self.model = model
        self.structured_call = structured_call

    def propose(self, *, requirements: str, analysis: ProjectAnalysis) -> dict[str, Any]:
        system_prompt = """
You are the project-level Architect for Nightshift.

Translate human-written product requirements into a safe backlog plan.
You do not write code and you do not modify existing tasks.

Rules:
- Inspect the current code, project knowledge, and full backlog before planning.
- Do not recreate work already implemented or already represented in the backlog.
- Preserve existing behavior unless the human requirement explicitly changes it.
- Resolve contradictions between new requirements and implemented behavior by creating
  a small clarification or migration task; do not silently choose one interpretation.
- Create small, ordered, independently verifiable tasks.
- Each task must name every project-relative file it may modify.
- Put tests in the same task as the behavior they verify when practical.
- Prompts must state observable behavior, error channels, exit codes, compatibility,
  and edge cases whenever relevant.
- Use run_tests=false only when no executable verification is meaningful.
- Return only new features or new tasks to append. Never return existing tasks.
- Task and feature IDs must not collide with any existing ID.
"""
        user_prompt = f"""
HUMAN REQUIREMENTS:

{requirements.strip()}

CURRENT PROJECT ANALYSIS:

{analysis.render()}

Produce a concise planning summary and backlog additions matching the schema.
"""
        plan = self.structured_call(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ARCHITECT_PLAN_SCHEMA,
        )
        Draft202012Validator(ARCHITECT_PLAN_SCHEMA).validate(plan)
        return plan


class BacklogGenerator:
    """Merge architect proposals into the current backlog without rewriting history."""

    def generate(
        self,
        *,
        current_backlog: dict[str, Any],
        proposal: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        Draft202012Validator(ARCHITECT_PLAN_SCHEMA).validate(proposal)
        timestamp = (now or datetime.now(timezone.utc)).isoformat()
        merged = json.loads(json.dumps(current_backlog))
        features = merged.setdefault("features", [])

        existing_feature_ids = {feature["id"] for feature in features}
        existing_task_ids = {
            task["id"] for feature in features for task in feature.get("tasks", [])
        }
        proposed_task_ids: set[str] = set()

        for proposed_feature in proposal["features"]:
            feature_id = proposed_feature["id"]
            target = next(
                (feature for feature in features if feature["id"] == feature_id),
                None,
            )
            if target is None:
                target = {
                    "id": feature_id,
                    "title": proposed_feature["title"],
                    "tasks": [],
                }
                features.append(target)
                existing_feature_ids.add(feature_id)
            elif target.get("title") != proposed_feature["title"]:
                raise ValueError(
                    f"Architect attempted to rename existing feature '{feature_id}'"
                )

            for proposed_task in proposed_feature["tasks"]:
                task_id = proposed_task["id"]
                if task_id in existing_task_ids or task_id in proposed_task_ids:
                    raise ValueError(f"Duplicate architect task id: {task_id}")
                proposed_task_ids.add(task_id)
                task = {
                    "id": task_id,
                    "title": proposed_task["title"],
                    "prompt": proposed_task["prompt"],
                    "files": proposed_task["files"],
                    "status": "pending",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
                if proposed_task.get("run_tests", True) is False:
                    task["run_tests"] = False
                target["tasks"].append(task)

        return merged


class BacklogWriter:
    """Validate and atomically persist the backlog source of truth."""

    def __init__(self, schema_path: Path | None = None) -> None:
        self.schema_path = schema_path or (
            Path(__file__).resolve().parent / "schema" / "backlog.schema.json"
        )

    def validate(self, backlog: dict[str, Any]) -> None:
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(backlog)

    def write(self, path: Path, backlog: dict[str, Any]) -> None:
        self.validate(backlog)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(backlog, indent=2, ensure_ascii=False) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


def render_architect_report(
    *,
    proposal: dict[str, Any],
    dry_run: bool,
    backlog_path: Path,
) -> str:
    task_count = sum(len(feature["tasks"]) for feature in proposal["features"])
    lines = [
        "Nightshift Architect",
        f"Summary: {proposal['summary']}",
        f"Features proposed: {len(proposal['features'])}",
        f"Tasks proposed: {task_count}",
    ]
    for feature in proposal["features"]:
        lines.append(f"\n{feature['id']}: {feature['title']}")
        for task in feature["tasks"]:
            lines.append(f"  - {task['id']}: {task['title']}")
    if dry_run:
        lines.append("\nDry run: backlog was not modified.")
    else:
        lines.append(f"\nBacklog updated: {backlog_path}")
    return "\n".join(lines)
