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
        "entries": [],
    },
    "adr.json": {"schema_version": "1.0", "decisions": []},
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


def test_load_exposes_validated_project_documents(tmp_path: Path) -> None:
    configuration = Configuration.load(create_project(tmp_path))

    assert configuration.context.project_root == tmp_path.resolve()
    assert configuration.project["project"]["id"] == "example"
    assert configuration.backlog["features"] == []
    assert configuration.knowledge["scope"] == "project"
    assert configuration.adr["decisions"] == []


def test_configuration_uses_supplied_schema_root(tmp_path: Path) -> None:
    project_root = create_project(tmp_path / "project")
    schema_root = Path(__file__).resolve().parent / "schema"

    configuration = Configuration.load(project_root, schema_root=schema_root)

    assert configuration.context.project_root == project_root.resolve()
