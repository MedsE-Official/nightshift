from pathlib import Path

from project_context import ProjectContext


def test_project_context_resolves_project_root(tmp_path):
    relative_root = tmp_path / "project" / ".." / "project"

    context = ProjectContext(relative_root)

    assert context.project_root == (tmp_path / "project").resolve()


def test_project_context_exposes_conventional_paths(tmp_path):
    context = ProjectContext(tmp_path)

    assert context.nightshift_root == tmp_path / ".nightshift"
    assert context.project_file == tmp_path / ".nightshift" / "project.json"
    assert context.backlog_file == tmp_path / ".nightshift" / "backlog.json"
    assert context.knowledge_file == tmp_path / ".nightshift" / "knowledge.json"
    assert context.adr_file == tmp_path / ".nightshift" / "adr.json"


def test_is_nightshift_project_requires_nightshift_directory(tmp_path):
    context = ProjectContext(tmp_path)

    assert context.is_nightshift_project() is False

    context.nightshift_root.mkdir()

    assert context.is_nightshift_project() is True
