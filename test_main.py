from types import SimpleNamespace
from unittest.mock import patch

import main


def test_main_routes_project_data_through_configuration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    configuration = SimpleNamespace(backlog={"features": []})

    with (
        patch("main.bootstrap", return_value=configuration) as bootstrap,
        patch("main.Planner.from_configuration") as from_configuration,
        patch("main.execute_next_task", return_value=None),
    ):
        result = main.main()

    assert result == 0
    bootstrap.assert_called_once_with(tmp_path.resolve())
    from_configuration.assert_called_once_with(configuration)
