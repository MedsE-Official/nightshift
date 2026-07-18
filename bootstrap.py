"""Bootstrap a Nightshift-enabled target repository."""

from pathlib import Path

from configuration import Configuration


def bootstrap(project_root: Path) -> Configuration:
    """Return the validated configuration for a target project."""

    return Configuration.load(project_root)
