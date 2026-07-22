"""Command-line entry point for running Nightshift against an external project."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from bootstrap import bootstrap
from main import load_runtime_config
from orchestrator import execute_next_task
from planner import Planner
from project_loader import ProjectLoadError


FRAMEWORK_ROOT = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one Nightshift cycle against an external project repository."
    )
    parser.add_argument(
        "project_root",
        type=Path,
        help="Path to the external project that contains .nightshift/.",
    )
    parser.add_argument(
        "--runtime-config",
        type=Path,
        default=FRAMEWORK_ROOT / "config.json",
        help="Framework runtime config (default: Nightshift's config.json).",
    )
    return parser


def _validate_target(project_root: Path) -> Path:
    resolved = project_root.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Project root does not exist: {resolved}")
    if not (resolved / ".git").exists():
        raise ValueError(f"Project root is not a Git repository: {resolved}")
    if not (resolved / ".nightshift").is_dir():
        raise ValueError(f"Missing .nightshift directory: {resolved / '.nightshift'}")
    return resolved


def _result_approved(result: object) -> bool | None:
    approved = getattr(result, "approved", None)
    if isinstance(approved, bool):
        return approved

    review_result = getattr(result, "review_result", None)
    for attribute in ("approved", "passed"):
        value = getattr(review_result, attribute, None)
        if isinstance(value, bool):
            return value
    return None


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        project_root = _validate_target(args.project_root)
        runtime_config_path = args.runtime_config.expanduser().resolve()
        runtime_config = load_runtime_config(runtime_config_path)
        configuration = bootstrap(project_root)
    except (OSError, ValueError, ProjectLoadError) as error:
        print(f"Nightshift could not start: {error}")
        return 2

    planner = Planner.from_configuration(configuration)
    result = execute_next_task(
        planner=planner,
        configuration=configuration,
        config=runtime_config,
    )

    if result is None:
        print(f"No task was available in {project_root}.")
        return 0

    approved = _result_approved(result)
    if approved is True:
        print(f"Nightshift cycle completed and was approved for {project_root}.")
        return 0
    if approved is False:
        print(f"Nightshift cycle completed but was not approved for {project_root}.")
        return 1

    print(f"Nightshift cycle completed for {project_root}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
