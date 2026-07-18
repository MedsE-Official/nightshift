from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from contracts import ArchitectureContract


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


@dataclass(frozen=True)
class ArchitectureApproval:
    contract_id: str
    decision: ApprovalDecision
    comment: str = ""


class ArchitectureApprovalRequired(RuntimeError):
    def __init__(self, contract_path: Path, approval_path: Path):
        super().__init__(
            "Architecture approval required. Review "
            f"{contract_path} and write approval to {approval_path}."
        )
        self.contract_path = contract_path
        self.approval_path = approval_path


def require_architecture_approval(
    *,
    contract: ArchitectureContract,
    directory: Path,
    policy: str,
) -> ArchitectureApproval:
    directory.mkdir(parents=True, exist_ok=True)
    contract_path = directory / "architecture_contract.json"
    approval_path = directory / "architecture_approval.json"
    contract_path.write_text(
        json.dumps(contract.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if policy == "auto":
        return ArchitectureApproval(contract.id, ApprovalDecision.APPROVED, "auto")
    if policy != "file":
        raise ValueError("architecture_approval_policy must be 'auto' or 'file'")
    if not approval_path.exists():
        raise ArchitectureApprovalRequired(contract_path, approval_path)

    data: Any = json.loads(approval_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Architecture approval must be a JSON object")
    if data.get("contract_id") != contract.id:
        raise ValueError("Architecture approval does not match contract id")
    try:
        decision = ApprovalDecision(data.get("decision"))
    except ValueError as exc:
        raise ValueError("Invalid architecture approval decision") from exc
    approval = ArchitectureApproval(
        contract_id=contract.id,
        decision=decision,
        comment=str(data.get("comment", "")),
    )
    if decision is ApprovalDecision.PENDING:
        raise ArchitectureApprovalRequired(contract_path, approval_path)
    if decision is ApprovalDecision.REJECTED:
        raise RuntimeError(f"Architecture contract rejected: {approval.comment}")
    return approval
