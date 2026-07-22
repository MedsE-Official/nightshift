from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import main_cli


def _target(tmp_path: Path) -> Path:
    root = tmp_path / "calculator"
    (root / ".git").mkdir(parents=True)
    (root / ".nightshift").mkdir()
    return root


def test_validate_target_accepts_external_git_repository(tmp_path):
    root = _target(tmp_path)
    assert main_cli._validate_target(root) == root.resolve()


def test_main_runs_one_cycle_against_external_project(monkeypatch, tmp_path):
    root = _target(tmp_path)
    configuration = SimpleNamespace(context=SimpleNamespace(project_root=root.resolve()))
    planner = Mock()
    result = SimpleNamespace(review_result=SimpleNamespace(passed=True))

    monkeypatch.setattr(main_cli, "load_runtime_config", lambda path: {"commands": {"test": "pytest -q"}})
    monkeypatch.setattr(main_cli, "bootstrap", lambda project_root: configuration)
    monkeypatch.setattr(main_cli.Planner, "from_configuration", lambda value: planner)
    execute = Mock(return_value=result)
    monkeypatch.setattr(main_cli, "execute_next_task", execute)

    assert main_cli.main([str(root)]) == 0
    execute.assert_called_once_with(
        planner=planner,
        configuration=configuration,
        config={"commands": {"test": "pytest -q"}},
    )


def test_main_returns_two_for_invalid_target(tmp_path):
    assert main_cli.main([str(tmp_path / "missing")]) == 2
