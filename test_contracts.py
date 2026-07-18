import pytest

from contracts import ArchitectureContract, contract_change_violations


def make_contract(**overrides):
    data = {
        "id": "arch-1",
        "goal": "Refactor planner",
        "summary": "Use one domain model.",
        "allowed_files": ["planner.py", "test_planner.py"],
        "forbidden_files": ["backlog.py", "orchestrator.py"],
        "required_changes": ["Remove PlannerTask", "Use Backlog"],
        "preserved_api": ["Planner.next_builder_task"],
        "removed_api": ["PlannerTask"],
        "risks": ["Existing imports may break"],
        "acceptance": ["Tests pass", "PlannerTask is absent"],
    }
    data.update(overrides)
    return ArchitectureContract.from_dict(data)


def test_architecture_contract_round_trip():
    contract = make_contract()

    assert contract.id == "arch-1"
    assert contract.allowed_files == ("planner.py", "test_planner.py")
    assert ArchitectureContract.from_dict(contract.to_dict()) == contract


def test_architecture_contract_rejects_overlap():
    with pytest.raises(ValueError, match="both allow and forbid"):
        make_contract(forbidden_files=["planner.py"])


def test_architecture_contract_requires_implementation_scope():
    with pytest.raises(ValueError, match="allow at least one file"):
        make_contract(allowed_files=[])


def test_contract_change_violations_are_deterministic():
    contract = make_contract()

    assert contract_change_violations(
        ["planner.py", "backlog.py", "README.md"],
        contract,
    ) == [
        "File changed outside architecture contract: README.md",
        "Forbidden file changed: backlog.py",
    ]
