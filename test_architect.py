from unittest.mock import patch

import pytest

from architect import ARCHITECTURE_SCHEMA, create_architecture_contract
from contracts import ArchitectureContract


VALID_RESPONSE = {
    "id": "arch-block-1",
    "goal": "Implement the block",
    "summary": "A narrow implementation design.",
    "allowed_files": ["example.py", "test_example.py"],
    "forbidden_files": ["orchestrator.py"],
    "required_changes": ["Add behavior", "Add tests"],
    "preserved_api": ["example.public_api"],
    "removed_api": [],
    "risks": ["Regression"],
    "acceptance": ["Tests pass"],
}


def test_architect_produces_typed_contract():
    with patch("architect.ollama_structured", return_value=VALID_RESPONSE) as call:
        contract = create_architecture_contract(
            model="test-model",
            task="Original feature",
            block={
                "id": "block-1",
                "title": "Example",
                "files": ["example.py", "test_example.py"],
            },
            project_snapshot="clean",
            config={"max_files_to_modify": 2},
        )

    assert isinstance(contract, ArchitectureContract)
    assert contract.allowed_files == ("example.py", "test_example.py")
    assert call.call_args.kwargs["schema"] == ARCHITECTURE_SCHEMA
    assert "You are the Architect" in call.call_args.kwargs["system_prompt"]


def test_architect_cannot_expand_planner_file_scope():
    response = {**VALID_RESPONSE, "allowed_files": ["unplanned.py"]}

    with patch("architect.ollama_structured", return_value=response):
        with pytest.raises(ValueError, match="outside Planner block"):
            create_architecture_contract(
                model="test-model",
                task="Feature",
                block={"id": "block-1", "files": ["example.py"]},
                project_snapshot="clean",
            )


def test_architect_respects_max_files_to_modify():
    with patch("architect.ollama_structured", return_value=VALID_RESPONSE):
        with pytest.raises(ValueError, match="max_files_to_modify"):
            create_architecture_contract(
                model="test-model",
                task="Feature",
                block={
                    "id": "block-1",
                    "files": ["example.py", "test_example.py"],
                },
                project_snapshot="clean",
                config={"max_files_to_modify": 1},
            )
