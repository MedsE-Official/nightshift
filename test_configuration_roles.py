from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from builder import Builder, BuilderResult, BuilderStatus, BuilderTask
from review import Reviewer
from test_runner import ExecutionResult


def fake_configuration(tmp_path: Path):
    return SimpleNamespace(
        context=SimpleNamespace(project_root=tmp_path),
        role_context=lambda role: f"{role.upper()} GUIDANCE",
    )


def test_builder_uses_configuration_project_root_and_guidance(tmp_path):
    configuration = fake_configuration(tmp_path)
    expected = BuilderResult(0, "", "", True, BuilderStatus.SUCCESS)

    with patch("builder.run_builder", return_value=expected) as run_builder:
        result = Builder.from_configuration(configuration).run(
            task=BuilderTask("Do work.", (Path("a.py"),)),
            runtime_config={"timeout_minutes_per_aider_run": 2},
        )

    assert result is expected
    called_task = run_builder.call_args.kwargs["task"]
    assert "BUILDER GUIDANCE" in called_task.prompt
    assert "Do work." in called_task.prompt
    assert run_builder.call_args.kwargs["project_root"] == tmp_path
    assert run_builder.call_args.kwargs["timeout_seconds"] == 120


def test_reviewer_uses_configuration_project_root_and_guidance(tmp_path):
    configuration = fake_configuration(tmp_path)

    with patch("review.run_review") as run_review:
        Reviewer.from_configuration(configuration).run(
            runtime_config={},
            block={"prompt": "Do work.", "files": ["a.py"]},
            diff="diff",
            builder_result=SimpleNamespace(),
            test_result=ExecutionResult(0, "", ""),
        )

    kwargs = run_review.call_args.kwargs
    assert kwargs["project_root"] == tmp_path
    assert kwargs["block"]["review_guidance"] == "REVIEWER GUIDANCE"
