from pathlib import Path
from unittest.mock import patch

from aider_workflow import build_aider_prompt, run_aider
from contracts import ArchitectureContract
from ollama_workflow import review_block


def contract():
    return ArchitectureContract.from_dict(
        {
            "id": "arch-1",
            "goal": "Change example",
            "summary": "Implement without redesign.",
            "allowed_files": ["example.py"],
            "forbidden_files": ["orchestrator.py"],
            "required_changes": ["Add example"],
            "preserved_api": [],
            "removed_api": [],
            "risks": [],
            "acceptance": ["Tests pass"],
        }
    )


def test_builder_prompt_treats_architecture_as_contract():
    prompt = build_aider_prompt(
        task="Feature",
        block={"id": "block-1", "files": ["example.py"]},
        attempt=1,
        previous_review=None,
        architecture_contract=contract(),
    )

    assert "You are the Builder" in prompt
    assert "Do not redesign" in prompt
    assert '"allowed_files": [\n    "example.py"' in prompt


def test_run_aider_receives_only_architect_allowed_files(tmp_path):
    with patch("aider_workflow.run_command") as command:
        run_aider(
            project_root=tmp_path,
            config={
                "timeout_minutes_per_aider_run": 1,
                "aider_model": "test-model",
                "commands": {},
            },
            prompt="Implement",
            block={"files": ["example.py", "unapproved.py"]},
            architecture_contract=contract(),
        )

    arguments = command.call_args.args[0]
    assert "example.py" in arguments
    assert "unapproved.py" not in arguments


def test_reviewer_receives_contract_and_violations():
    with patch(
        "ollama_workflow.ollama_structured",
        return_value={
            "approved": False,
            "summary": "Violation",
            "requirements": [],
            "required_fixes": ["Revert orchestrator.py"],
        },
    ) as structured:
        review_block(
            model="test-model",
            task="Feature",
            block={"id": "block-1"},
            diff="diff",
            verification={},
            protected_violations=[],
            architecture_contract=contract(),
            contract_violations=["Forbidden file changed: orchestrator.py"],
        )

    user_prompt = structured.call_args.kwargs["user_prompt"]
    assert "ARCHITECTURE CONTRACT" in user_prompt
    assert "Forbidden file changed: orchestrator.py" in user_prompt
