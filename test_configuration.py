import json
from pathlib import Path

from configuration import Configuration


VALID_DOCUMENTS = {
    "project.json": {
        "schema_version": "1.0",
        "project": {"id": "example", "name": "Example"},
    },
    "backlog.json": {"schema_version": "1.0", "features": []},
    "knowledge.json": {
        "schema_version": "1.0",
        "scope": "project",
        "entries": [
            {
                "id": "simple",
                "title": "Simple",
                "content": "Keep it simple.",
                "tags": ["builder"],
            }
        ],
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


def create_project(tmp_path: Path) -> Path:
    nightshift_root = tmp_path / ".nightshift"
    nightshift_root.mkdir(parents=True)
    for filename, content in VALID_DOCUMENTS.items():
        (nightshift_root / filename).write_text(
            json.dumps(content),
            encoding="utf-8",
        )
    return tmp_path


def test_load_exposes_all_validated_project_documents(tmp_path: Path) -> None:
    configuration = Configuration.load(create_project(tmp_path))

    assert configuration.project["project"]["id"] == "example"
    assert configuration.backlog["features"] == []
    assert configuration.knowledge["scope"] == "project"
    assert configuration.adr["decisions"] == []
    assert configuration.prompts["prompts"]["builder"] == "Build."


def test_role_context_combines_prompt_and_project_knowledge(tmp_path: Path) -> None:
    configuration = Configuration.load(create_project(tmp_path))

    context = configuration.role_context("builder")

    assert "Build." in context
    assert "Keep it simple." in context
