import os
from enum import Enum
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
from api_guard import check_public_api, ApiGuardResult
from builder import BuilderResult, BuilderStatus


class ReviewStatus(Enum):
    PASSED = "passed"
    BUILDER_FAILED = "builder_failed"
    BUILDER_TIMEOUT = "builder_timeout"
    NO_CHANGES = "no_changes"
    TESTS_FAILED = "tests_failed"
    API_GUARD_FAILED = "api_guard_failed"
    UNEXPECTED_STATUS = "unexpected_status"


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
    status: "ReviewStatus"


@dataclass(frozen=True)
class ReviewSummary:
    builder_status: BuilderStatus
    review_status: ReviewStatus
    passed: bool
    errors: tuple[str, ...]

    @property
    def failed(self) -> bool:
        return not self.passed


@dataclass(frozen=True)
class ExecutionResult:
    return_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0


def run_review(
    *,
    project_root: Path,
    config: Dict[str, Any],
    block: Dict[str, Any],
    diff: str,
    builder_result: BuilderResult,
    test_result: ExecutionResult,
) -> ReviewResult:
    """
    Run the review process.
    
    Args:
        project_root: Root directory of the project
        config: Configuration dictionary
        block: Block information
        diff: Git diff
        builder_result: Result from the builder execution
        
    Returns:
        Review results
    """
    # Handle different builder statuses before running API Guard
    if builder_result.status == BuilderStatus.FAILED:
        return ReviewResult(
            passed=False,
            errors=("Builder execution failed.",),
            status=ReviewStatus.BUILDER_FAILED
        )
    elif builder_result.status == BuilderStatus.TIMEOUT:
        return ReviewResult(
            passed=False,
            errors=("Builder execution timed out.",),
            status=ReviewStatus.BUILDER_TIMEOUT
        )
    elif builder_result.status == BuilderStatus.NO_CHANGES:
        return ReviewResult(
            passed=False,
            errors=("Builder produced no file changes.",),
            status=ReviewStatus.NO_CHANGES
        )
    
    # Only run API guard check if builder succeeded
    if builder_result.status == BuilderStatus.SUCCESS:
        # Check test result before running API Guard
        if not test_result.passed:
            return ReviewResult(
                passed=False,
                errors=("Test execution failed.",),
                status=ReviewStatus.TESTS_FAILED
            )
        
        api_guard_result = _run_api_guard(
            project_root / "before.py",
            project_root / "after.py"
        )
        
        # Initialize errors
        errors = ()
        
        # Add API guard errors if check failed
        if not api_guard_result.passed:
            error_msg = f"Public API change detected: removed symbols {sorted(api_guard_result.removed_symbols)}"
            errors = (error_msg,)
        
        return ReviewResult(
            passed=api_guard_result.passed,
            errors=errors,
            status=ReviewStatus.PASSED if api_guard_result.passed else ReviewStatus.API_GUARD_FAILED
        )
    
    # Default case - should not happen with valid BuilderStatus values
    return ReviewResult(
        passed=False,
        errors=("Unexpected builder status.",),
        status=ReviewStatus.UNEXPECTED_STATUS
    )


def to_summary(review_result: ReviewResult, builder_result: BuilderResult) -> ReviewSummary:
    """Convert a ReviewResult and BuilderResult to a ReviewSummary."""
    return ReviewSummary(
        builder_status=builder_result.status,
        review_status=review_result.status,
        passed=review_result.passed,
        errors=review_result.errors
    )
