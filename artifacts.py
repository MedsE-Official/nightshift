from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class CycleIdentity:
    feature_id: str
    task_id: str
    cycle_id: str
    nightshift_version: str
    commit: str


def current_commit(project_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


class ArtifactStore:
    def __init__(self, root: Path, identity: CycleIdentity) -> None:
        self.root = root / identity.feature_id / identity.task_id / identity.cycle_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.write_json("identity.json", asdict(identity))

    def write_json(self, name: str, value: Mapping[str, Any] | list[Any]) -> Path:
        path = self.root / name
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        return path

    def write_text(self, name: str, value: str) -> Path:
        path = self.root / name
        path.write_text(value, encoding="utf-8")
        return path


class Historian:
    def record_retrospective(
        self,
        *,
        store: ArtifactStore,
        approved: bool,
        attempts: int,
        review: Mapping[str, Any],
        verification: Mapping[str, Any],
        contract_violations: list[str],
    ) -> Path:
        failed_checks = [
            name for name, result in verification.items() if not result.get("passed", False)
        ]
        went_well = []
        went_badly = []
        if approved:
            went_well.append("Implementation satisfied deterministic checks and review.")
        if attempts == 1:
            went_well.append("Builder completed the block on the first attempt.")
        if attempts > 1:
            went_badly.append(f"Builder required {attempts} attempts.")
        if failed_checks:
            went_badly.append("Verification failures: " + ", ".join(failed_checks))
        went_badly.extend(contract_violations)

        retrospective = {
            "went_well": went_well,
            "went_badly": went_badly,
            "continue": ["Use structured architecture contracts."],
            "stop": ["Changing files outside the approved contract"] if contract_violations else [],
            "try": ["Reduce task scope"] if attempts > 1 else [],
            "review_summary": review.get("summary", ""),
        }
        return store.write_json("retrospective.json", retrospective)
