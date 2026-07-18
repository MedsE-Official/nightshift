import json

import pytest

from approvals import ArchitectureApprovalRequired, require_architecture_approval
from contracts import ArchitectureContract


def contract():
    return ArchitectureContract.from_dict({
        "id": "arch-1", "goal": "g", "summary": "s",
        "allowed_files": ["a.py"], "forbidden_files": [],
        "required_changes": ["change"], "preserved_api": [], "removed_api": [],
        "risks": [], "acceptance": ["tests pass"],
    })


def test_file_approval_stops_before_builder(tmp_path):
    with pytest.raises(ArchitectureApprovalRequired):
        require_architecture_approval(contract=contract(), directory=tmp_path, policy="file")
    assert (tmp_path / "architecture_contract.json").exists()


def test_matching_approval_allows_execution(tmp_path):
    (tmp_path / "architecture_approval.json").write_text(json.dumps({
        "contract_id": "arch-1", "decision": "approved", "comment": "ok"
    }))
    result = require_architecture_approval(contract=contract(), directory=tmp_path, policy="file")
    assert result.decision.value == "approved"
