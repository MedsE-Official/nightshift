from pathlib import Path
from unittest.mock import patch

import pytest

import architect_cli


def write_requirements(
    project_root: Path,
    content: str = "Build a calculator",
) -> Path:
    nightshift_dir = project_root / ".nightshift"
    nightshift_dir.mkdir(parents=True, exist_ok=True)

    requirements_file = nightshift_dir / "requirements.md"
    requirements_file.write_text(content, encoding="utf-8")
    return requirements_file


def test_load_requirements_from_markdown(tmp_path):
    write_requirements(tmp_path, " Build a calculator ")

    assert architect_cli.load_requirements(tmp_path) == "Build a calculator"


def test_load_requirements_uses_resolved_project_root(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    write_requirements(project_root, "Build it")

    monkeypatch.chdir(tmp_path)

    assert architect_cli.load_requirements(Path("project")) == "Build it"


def test_load_requirements_raises_when_file_is_missing(tmp_path):
    expected_path = tmp_path.resolve() / ".nightshift" / "requirements.md"

    with pytest.raises(
        FileNotFoundError,
        match="Missing requirements document",
    ) as exc_info:
        architect_cli.load_requirements(tmp_path)

    assert str(expected_path) in str(exc_info.value)


def test_load_requirements_raises_when_file_is_empty(tmp_path):
    requirements_file = write_requirements(tmp_path, "   \n")

    with pytest.raises(
        ValueError,
        match="Requirements document is empty",
    ) as exc_info:
        architect_cli.load_requirements(tmp_path)

    assert str(requirements_file.resolve()) in str(exc_info.value)


def test_resolve_model_prefers_explicit_model():
    assert architect_cli.resolve_model("custom") == "custom"


def test_main_dry_run_prints_report_without_write(tmp_path, capsys):
    write_requirements(tmp_path, "Build it")
    proposal = {"summary": "Plan", "features": []}

    with patch.object(
        architect_cli,
        "run_architect",
        return_value=(proposal, {}),
    ) as run:
        result = architect_cli.main(
            [
                "--project-root",
                str(tmp_path),
                "--model",
                "test",
                "--dry-run",
            ]
        )

    assert result == 0
    assert "Dry run" in capsys.readouterr().out

    run.assert_called_once_with(
        project_root=tmp_path.resolve(),
        requirements="Build it",
        model="test",
        dry_run=True,
    )


def test_main_json_prints_raw_proposal(tmp_path, capsys):
    write_requirements(tmp_path, "Build it")
    proposal = {"summary": "Plan", "features": []}

    with patch.object(
        architect_cli,
        "run_architect",
        return_value=(proposal, {}),
    ):
        result = architect_cli.main(
            [
                "--project-root",
                str(tmp_path),
                "--model",
                "test",
                "--dry-run",
                "--json",
            ]
        )

    assert result == 0
    output = capsys.readouterr().out
    assert '"summary": "Plan"' in output


def test_main_exits_when_requirements_are_missing(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        architect_cli.main(
            [
                "--project-root",
                str(tmp_path),
                "--model",
                "test",
                "--dry-run",
            ]
        )

    assert exc_info.value.code == 1
    assert "Missing requirements document" in capsys.readouterr().err


def test_parser_rejects_removed_prompt_option():
    with pytest.raises(SystemExit) as exc_info:
        architect_cli.main(["--prompt", "Build it"])

    assert exc_info.value.code == 2


def test_parser_rejects_removed_requirements_option():
    with pytest.raises(SystemExit) as exc_info:
        architect_cli.main(["--requirements", "requirements.txt"])

    assert exc_info.value.code == 2