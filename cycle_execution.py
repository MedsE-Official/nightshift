from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from builder import Builder, BuilderResult, BuilderTask, run_builder
from configuration import Configuration
from git_tools import git_review_bundle
from planner import Planner
from review import Reviewer, ReviewResult, run_review
from test_runner import ExecutionResult, run_tests


@dataclass(frozen=True)
class CycleResult:
    builder_result: BuilderResult
    test_result: ExecutionResult
    review_result: ReviewResult


def execute_cycle(
    *,
    task: BuilderTask,
    config: dict[str, Any],
    configuration: Configuration | None = None,
    project_root: Path | None = None,
) -> CycleResult:
    """Execute one task.

    Configuration is the preferred project gateway. project_root remains as a
    compatibility seam for callers that have not yet migrated.
    """

    if configuration is not None:
        resolved_root = configuration.context.project_root
        builder_result = Builder.from_configuration(configuration).run(
            task=task,
            runtime_config=config,
        )
    else:
        if project_root is None:
            raise ValueError("configuration or project_root is required")
        resolved_root = Path(project_root)
        builder_result = run_builder(
            task=task,
            project_root=resolved_root,
            timeout_seconds=int(config["timeout_minutes_per_aider_run"]) * 60,
        )

    if configuration is not None:
        test_result = run_tests(
            project_root=resolved_root,
            config=config,
            run_test_command=task.run_tests,
        )
    else:
        test_result = (
            run_tests()
            if task.run_tests
            else run_tests(run_test_command=False)
        )
    diff = git_review_bundle(resolved_root)

    if configuration is not None:
        review_result = Reviewer.from_configuration(configuration).run(
            runtime_config=config,
            block=task.review_block,
            diff=diff,
            builder_result=builder_result,
            test_result=test_result,
        )
    else:
        review_result = run_review(
            project_root=resolved_root,
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
    config: dict[str, Any],
    configuration: Configuration | None = None,
    project_root: Path | None = None,
) -> CycleResult | None:
    builder_task = planner.next_builder_task()
    if builder_task is None:
        return None

    effective_configuration = configuration
    if effective_configuration is None and isinstance(planner, Planner):
        effective_configuration = planner.configuration
    if effective_configuration is None:
        result = execute_cycle(
            task=builder_task,
            project_root=project_root,
            config=config,
        )
    else:
        result = execute_cycle(
            task=builder_task,
            configuration=effective_configuration,
            project_root=project_root,
            config=config,
        )

    if result.review_result.passed:
        planner.complete_current_task()

    return result


def execute_all_tasks(
    *,
    planner: Planner,
    config: dict[str, Any],
    configuration: Configuration | None = None,
    project_root: Path | None = None,
) -> tuple[CycleResult, ...]:
    results: list[CycleResult] = []
    while True:
        result = execute_next_task(
            planner=planner,
            configuration=configuration,
            project_root=project_root,
            config=config,
        )
        if result is None:
            return tuple(results)
        results.append(result)


def execute_backlog(
    *,
    configuration: Configuration,
    config: dict[str, Any],
    project_root: Path | None = None,
) -> tuple[CycleResult, ...]:
    planner = Planner.from_configuration(configuration)
    return execute_all_tasks(
        planner=planner,
        project_root=project_root or configuration.context.project_root,
        config=config,
    )
