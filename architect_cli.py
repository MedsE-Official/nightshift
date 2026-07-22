from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from architect_planning import (
    ArchitectAgent,
    BacklogGenerator,
    BacklogWriter,
    ProjectAnalyzer,
    render_architect_report,
)
from configuration import Configuration


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="architect",
        description=(
            "Translate .nightshift/requirements.md into validated "
            "Nightshift backlog tasks."
        ),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Target project root.",
    )
    parser.add_argument(
        "--model",
        type=str,
        help=(
            "Ollama model. Defaults to the architect role "
            "in Nightshift config.json."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and validate a plan without modifying backlog.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw structured proposal instead of the human report.",
    )
    return parser


def load_requirements(project_root: Path) -> str:
    """Load the project's human-written product requirements."""

    resolved_root = Path(project_root).resolve()
    requirements_file = resolved_root / ".nightshift" / "requirements.md"

    if not requirements_file.is_file():
        raise FileNotFoundError(
            f"Missing requirements document: {requirements_file}"
        )

    requirements = requirements_file.read_text(encoding="utf-8").strip()

    if not requirements:
        raise ValueError(
            f"Requirements document is empty: {requirements_file}"
        )

    return requirements


def _load_framework_config() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "config.json"
    if not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"Framework config must contain a JSON object: {path}"
        )

    return data


def resolve_model(explicit_model: str | None) -> str:
    if explicit_model:
        return explicit_model

    config = _load_framework_config()
    roles = config.get("roles", {})
    architect = roles.get("architect", {}) if isinstance(roles, dict) else {}

    model = architect.get("model") if isinstance(architect, dict) else None
    model = model or config.get("model")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("No Architect model configured; pass --model")

    return model.strip()


def run_architect(
    *,
    project_root: Path,
    requirements: str,
    model: str,
    dry_run: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    configuration = Configuration.load(project_root)
    analysis = ProjectAnalyzer().analyze(configuration)

    proposal = ArchitectAgent(model=model).propose(
        requirements=requirements,
        analysis=analysis,
    )

    backlog = BacklogGenerator().generate(
        current_backlog=configuration.backlog,
        proposal=proposal,
    )

    writer = BacklogWriter()
    writer.validate(backlog)

    if not dry_run:
        writer.write(configuration.context.backlog_file, backlog)

    return proposal, backlog


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        project_root = args.project_root.resolve()
        requirements = load_requirements(project_root)
        model = resolve_model(args.model)

        proposal, _ = run_architect(
            project_root=project_root,
            requirements=requirements,
            model=model,
            dry_run=args.dry_run,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"Architect failed: {exc}\n")

    if args.json:
        print(json.dumps(proposal, indent=2, ensure_ascii=False))
    else:
        print(
            render_architect_report(
                proposal=proposal,
                dry_run=args.dry_run,
                backlog_path=project_root / ".nightshift" / "backlog.json",
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())