from __future__ import annotations

from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDED = {".git", ".venv", "__pycache__", ".pytest_cache", "history", "reports", "state"}


def build_repo_map(
    project_root: Path,
    *,
    candidate_files: Iterable[str] = (),
    max_files: int = 200,
) -> str:
    """Create a deterministic, compact repository map without using an LLM."""
    root = project_root.expanduser().resolve()
    candidates = {str(Path(path)) for path in candidate_files}
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in DEFAULT_EXCLUDED for part in relative.parts):
            continue
        if path.name.startswith(".DS_Store"):
            continue
        marker = "*" if str(relative) in candidates else "-"
        lines.append(f"{marker} {relative}")
        if len(lines) >= max_files:
            lines.append("... repository map truncated ...")
            break
    return "\n".join(lines) or "Repository contains no visible files."
