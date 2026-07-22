from pathlib import Path
from unittest.mock import call, patch

from test_runner import run_tests


def test_run_tests_skips_test_command_but_keeps_diff_check(tmp_path: Path):
    with patch("test_runner._run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        result = run_tests(
            project_root=tmp_path,
            config={"commands": {"test": "python -m pytest -q"}},
            run_test_command=False,
        )

    assert result.passed is True
    assert result.stdout == "Tests skipped by task configuration."
    mock_run.assert_called_once_with(
        ["git", "--no-pager", "diff", "--check"],
        cwd=tmp_path.resolve(),
    )


def test_run_tests_runs_configured_command_by_default(tmp_path: Path):
    with patch("test_runner._run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        result = run_tests(
            project_root=tmp_path,
            config={"commands": {"test": "python -m pytest -q"}},
        )

    assert result.passed is True
    assert mock_run.call_args_list == [
        call(["python", "-m", "pytest", "-q"], cwd=tmp_path.resolve()),
        call(["git", "--no-pager", "diff", "--check"], cwd=tmp_path.resolve()),
    ]
