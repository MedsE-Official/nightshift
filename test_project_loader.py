import json
from pathlib import Path

import pytest

from project_context import ProjectContext
from project_loader import ProjectLoadError, ProjectLoader


VALID_DOCUMENTS = {
    "project.json": {
        "schema_version": "1.0",
        "project": {"id": "example", "name": "Example"},
    },
    "backlog.json": {"schema_version": "1.0", "features": []},
    "knowledge.json": {
        "schema_version": "1.0",
        "scope": "project",
        "entries": [],
    },
    "adr.json": {"schema_version": "1.0", "decisions": []},
    "prompts.json": {
        "schema_version": "1.0",
        "prompts": {
            "planner": "Plan.",
            "builder": "Build.",
            "reviewer": "Review.",
            "architect": "Design.",
        },
    },
}


def create_project(tmp_path: Path) -> ProjectContext:
    nightshift_root = tmp_path / ".nightshift"
    nightshift_root.mkdir()
    for filename, content in VALID_DOCUMENTS.items():
        (nightshift_root / filename).write_text(
            json.dumps(content),
            encoding="utf-8",
        )
    return ProjectContext(tmp_path)


def test_loads_all_project_documents(tmp_path: Path) -> None:
    data = ProjectLoader(create_project(tmp_path)).load()

    assert data.project["project"]["id"] == "example"
    assert data.backlog["features"] == []
    assert data.knowledge["scope"] == "project"
    assert data.adr["decisions"] == []
    assert data.prompts["prompts"]["planner"] == "Plan."


def test_reports_missing_project_document(tmp_path: Path) -> None:
    context = create_project(tmp_path)
    context.backlog_file.unlink()

    with pytest.raises(ProjectLoadError, match="Missing project document"):
        ProjectLoader(context).load()


def test_reports_invalid_json_with_location(tmp_path: Path) -> None:
    context = create_project(tmp_path)
    context.project_file.write_text('{"schema_version":', encoding="utf-8")

    with pytest.raises(ProjectLoadError, match=r"Invalid JSON.*line 1"):
        ProjectLoader(context).load()


def test_reports_schema_validation_error(tmp_path: Path) -> None:
    context = create_project(tmp_path)
    context.project_file.write_text(
        json.dumps({"schema_version": "1.0", "project": {"id": "example"}}),
        encoding="utf-8",
    )

    with pytest.raises(ProjectLoadError, match=r"Invalid project document.*name"):
        ProjectLoader(context).load()
