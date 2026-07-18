from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Architecture contract field '{key}' must be an array of strings")
    return tuple(value)


@dataclass(frozen=True)
class ArchitectureContract:
    """Immutable handoff from Architect to Builder and Reviewer."""

    id: str
    goal: str
    summary: str
    allowed_files: tuple[str, ...]
    forbidden_files: tuple[str, ...]
    required_changes: tuple[str, ...]
    preserved_api: tuple[str, ...]
    removed_api: tuple[str, ...]
    risks: tuple[str, ...]
    acceptance: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArchitectureContract":
        if not isinstance(data, dict):
            raise ValueError("Architecture contract must be an object")

        required_strings = ("id", "goal", "summary")
        for key in required_strings:
            value = data.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Architecture contract field '{key}' must be a non-empty string"
                )

        contract = cls(
            id=data["id"].strip(),
            goal=data["goal"].strip(),
            summary=data["summary"].strip(),
            allowed_files=_string_tuple(data, "allowed_files"),
            forbidden_files=_string_tuple(data, "forbidden_files"),
            required_changes=_string_tuple(data, "required_changes"),
            preserved_api=_string_tuple(data, "preserved_api"),
            removed_api=_string_tuple(data, "removed_api"),
            risks=_string_tuple(data, "risks"),
            acceptance=_string_tuple(data, "acceptance"),
        )
        contract.validate()
        return contract

    def validate(self) -> None:
        if not self.allowed_files:
            raise ValueError("Architecture contract must allow at least one file")
        overlap = set(self.allowed_files) & set(self.forbidden_files)
        if overlap:
            raise ValueError(
                "Architecture contract cannot both allow and forbid: "
                + ", ".join(sorted(overlap))
            )
        if not self.required_changes:
            raise ValueError("Architecture contract must contain required changes")
        if not self.acceptance:
            raise ValueError("Architecture contract must contain acceptance criteria")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "summary": self.summary,
            "allowed_files": list(self.allowed_files),
            "forbidden_files": list(self.forbidden_files),
            "required_changes": list(self.required_changes),
            "preserved_api": list(self.preserved_api),
            "removed_api": list(self.removed_api),
            "risks": list(self.risks),
            "acceptance": list(self.acceptance),
        }


def contract_change_violations(
    changed_files: Iterable[str],
    contract: ArchitectureContract,
) -> list[str]:
    """Return deterministic file-scope violations for a completed build attempt."""

    allowed = set(contract.allowed_files)
    forbidden = set(contract.forbidden_files)
    violations: list[str] = []

    for file_name in sorted(set(changed_files)):
        if file_name in forbidden:
            violations.append(f"Forbidden file changed: {file_name}")
        elif file_name not in allowed:
            violations.append(f"File changed outside architecture contract: {file_name}")

    return violations
