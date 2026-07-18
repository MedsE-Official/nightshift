import json
from pathlib import Path

from bootstrap import bootstrap
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


def test_bootstrap_returns_configuration_gateway(tmp_path: Path) -> None:
    nightshift_root = tmp_path / ".nightshift"
    nightshift_root.mkdir()
    for filename, content in VALID_DOCUMENTS.items():
        (nightshift_root / filename).write_text(
            json.dumps(content),
            encoding="utf-8",
        )

    configuration = bootstrap(tmp_path)

    assert isinstance(configuration, Configuration)
    assert configuration.project["project"]["name"] == "Example"
