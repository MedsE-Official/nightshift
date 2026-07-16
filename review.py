import os
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
from api_guard import check_public_api, ApiGuardResult


def _run_api_guard(
    before_file: Path,
    after_file: Path,
) -> ApiGuardResult:
    """
    Run API guard check on the given files.
    
    Args:
        before_file: Path to the previous version of a Python file
        after_file: Path to the current version of a Python file
        
    Returns:
        An ApiGuardResult indicating whether the check passed and any removed symbols
    """
    return check_public_api(before_file, after_file)


@dataclass(frozen=True)
class ReviewResult:
    passed: bool
    errors: tuple[str, ...]


def run_review(
    *,
    project_root: Path,
    config: Dict[str, Any],
    block: Dict[str, Any],
    diff: str,
) -> Dict[str, Any]:
    """
    Run the review process.
    
    Args:
        project_root: Root directory of the project
        config: Configuration dictionary
        block: Block information
        diff: Git diff
        
    Returns:
        Review results
    """
    # Run API guard check
    api_guard_result = _run_api_guard(
        project_root / "before.py",
        project_root / "after.py"
    )
    
    # Initialize review result
    review_result = {
        "review": "placeholder",
        "api_guard_result": api_guard_result,
    }
    
    # Add API guard errors if check failed
    if not api_guard_result.passed:
        if "errors" not in review_result:
            review_result["errors"] = []
        error_msg = f"Public API change detected: removed symbols {sorted(api_guard_result.removed_symbols)}"
        review_result["errors"].append(error_msg)
    
    return review_result
