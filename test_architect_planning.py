import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from architect_planning import (
    ArchitectAgent,
    BacklogGenerator,
    BacklogWriter,
    ProjectAnalysis,
    SourceTreeAnalyzer,
    SourceTreeSnapshot,
)


def proposal():
    return {
        "summary": "Add CLI behavior",
        "features": [
            {
                "id": "cli",
                "title": "CLI",
                "tasks": [
                    {
                        "id": "CLI-001",
                        "title": "Add CLI",
                        "prompt": "Add explicit stdout and stderr behavior.",
                        "files": ["main.py", "test_main.py"],
                    }
                ],
            }
        ],
    }


def test_source_tree_analyzer_excludes_control_and_reads_sources(tmp_path):
    (tmp_path / "app.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / ".nightshift").mkdir()
    (tmp_path / ".nightshift" / "backlog.json").write_text("{}", encoding="utf-8")

    snapshot = SourceTreeAnalyzer().analyze(tmp_path)

    assert snapshot.files == ("app.py",)
    assert snapshot.excerpts["app.py"] == "print('ok')"


def test_architect_agent_uses_structured_schema():
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        return proposal()

    analysis = ProjectAnalysis(
        project={"schema_version": "1.0", "project": {"id": "x", "name": "X"}},
        backlog={"schema_version": "1.0", "features": []},
        knowledge={"schema_version": "1.0", "scope": "project", "entries": []},
        source_tree=SourceTreeSnapshot(files=("main.py",), excerpts={}),
    )

    result = ArchitectAgent(model="test", structured_call=fake_call).propose(
        requirements="Build a CLI", analysis=analysis
    )

    assert result == proposal()
    assert calls[0]["model"] == "test"
    assert "CURRENT PROJECT ANALYSIS" in calls[0]["user_prompt"]


def test_backlog_generator_appends_task_and_sets_timestamps():
    current = {
        "schema_version": "1.0",
        "features": [{"id": "cli", "title": "CLI", "tasks": []}],
    }
    now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)

    merged = BacklogGenerator().generate(
        current_backlog=current, proposal=proposal(), now=now
    )

    task = merged["features"][0]["tasks"][0]
    assert task["status"] == "pending"
    assert task["created_at"] == now.isoformat()
    assert current["features"][0]["tasks"] == []


def test_backlog_generator_rejects_existing_task_id():
    current = {
        "schema_version": "1.0",
        "features": [
            {
                "id": "old",
                "title": "Old",
                "tasks": [
                    {
                        "id": "CLI-001",
                        "title": "Existing",
                        "prompt": "Existing",
                        "files": [],
                        "status": "pending",
                        "created_at": "2026-07-22T00:00:00+00:00",
                        "updated_at": "2026-07-22T00:00:00+00:00",
                    }
                ],
            }
        ],
    }

    with pytest.raises(ValueError, match="Duplicate architect task id"):
        BacklogGenerator().generate(current_backlog=current, proposal=proposal())


def test_backlog_writer_validates_and_writes_atomically(tmp_path):
    schema_path = Path(__file__).resolve().parent / "schema" / "backlog.schema.json"
    writer = BacklogWriter(schema_path)
    backlog = BacklogGenerator().generate(
        current_backlog={"schema_version": "1.0", "features": []},
        proposal=proposal(),
    )
    target = tmp_path / "backlog.json"

    writer.write(target, backlog)

    assert json.loads(target.read_text(encoding="utf-8")) == backlog
