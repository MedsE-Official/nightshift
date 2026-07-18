from __future__ import annotations

from configuration import Configuration

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from builder import BuilderResult, BuilderTask, run_builder
from planner import Planner
from review import ReviewResult, run_review
from test_runner import ExecutionResult, run_tests
from git_tools import git_review_bundle


@dataclass(frozen=True)
class CycleResult:
    builder_result: BuilderResult
    test_result: ExecutionResult
    review_result: ReviewResult


def execute_cycle(
    *,
    task: BuilderTask,
    project_root: Path,
    config: dict[str, Any],
) -> CycleResult:
    builder_result = run_builder(
        task=task,
        project_root=project_root,
        timeout_seconds=int(config["timeout_minutes_per_aider_run"]) * 60,
    )
    test_result = run_tests()
    diff = git_review_bundle(project_root)
    review_result = run_review(
        project_root=project_root,
        config=config,
        block=task.review_block,
        diff=diff,
        builder_result=builder_result,
        test_result=test_result,
    )
    return CycleResult(
        builder_result=builder_result,
        test_result=test_result,
        review_result=review_result,
    )


def execute_next_task(
    *,
    planner: Planner,
    project_root: Path,
    config: dict[str, Any],
) -> CycleResult | None:
    builder_task = planner.next_builder_task()
    if builder_task is None:
        return None
    return execute_cycle(
        task=builder_task,
        project_root=project_root,
        config=config,
    )


def execute_all_tasks(
    *,
    planner: Planner,
    project_root: Path,
    config: dict[str, Any],
) -> tuple[CycleResult, ...]:
    results: list[CycleResult] = []
    while True:
        result = execute_next_task(
            planner=planner,
            project_root=project_root,
            config=config,
        )
        if result is None:
            return tuple(results)
        results.append(result)


def execute_backlog(
    *,
    configuration: Configuration,
    project_root: Path,
    config: dict[str, Any],
) -> tuple[CycleResult, ...]:
    """Execute the validated project backlog from Configuration."""

    return execute_all_tasks(
        planner=Planner.from_configuration(configuration),
        project_root=project_root,
        config=config,
    )
