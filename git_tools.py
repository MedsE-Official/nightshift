from __future__ import annotations

from pathlib import Path

from orchestrator_runtime import run_command
def git_status(project_root: Path) -> str:
    result = run_command(
        ["git", "--no-pager", "status", "--short"],
        cwd=project_root,
        timeout_seconds=30,
    )
    return result.stdout.strip()


def changed_files(project_root: Path) -> list[str]:
    result = run_command(
        ["git", "--no-pager", "status", "--porcelain"],
        cwd=project_root,
        timeout_seconds=30,
    )

    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        # Porcelain format: XY<space>path
        path = line[3:].strip()

        # Renames are represented as "old -> new".
        if " -> " in path:
            path = path.split(" -> ", 1)[1]

        files.append(path)

    return sorted(set(files))


def git_review_bundle(project_root: Path, max_chars: int = 60_000) -> str:
    tracked_diff = run_command(
        [
            "git",
            "--no-pager",
            "diff",
            "--no-ext-diff",
            "--unified=40",
            "--",
        ],
        cwd=project_root,
        timeout_seconds=60,
    ).stdout

    untracked = run_command(
        [
            "git",
            "--no-pager",
            "ls-files",
            "--others",
            "--exclude-standard",
        ],
        cwd=project_root,
        timeout_seconds=30,
    ).stdout.splitlines()

    sections = [tracked_diff]

    for relative_name in untracked:
        path = project_root / relative_name
        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            sections.append(
                f"\n--- UNTRACKED BINARY/UNREADABLE FILE: {relative_name} ---\n"
            )
            continue

        sections.append(
            f"\n--- UNTRACKED FILE: {relative_name} ---\n"
            f"{content[:20_000]}"
        )

    return "\n".join(sections)[-max_chars:]


def detect_protected_changes(
    files: list[str],
    protected_paths: list[str],
) -> list[str]:
    violations: list[str] = []

    for filename in files:
        for protected in protected_paths:
            protected_normalized = protected.rstrip("/")

            if (
                filename == protected_normalized
                or filename.startswith(protected_normalized + "/")
            ):
                violations.append(filename)

    return sorted(set(violations))


def git_checkpoint(project_root: Path) -> str:
    """Return the current HEAD commit as a checkpoint."""

    result = run_command(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        timeout_seconds=30,
    )

    if not result.passed:
        raise RuntimeError(
            "Could not determine the current Git commit."
        )

    checkpoint = result.stdout.strip()

    if not checkpoint:
        raise RuntimeError(
            "Git returned an empty checkpoint commit."
        )

    return checkpoint


def git_restore_checkpoint(
    project_root: Path,
    checkpoint_commit: str,
) -> None:
    """Restore the working tree to a checkpoint commit."""

    result = run_command(
        ["git", "reset", "--hard", checkpoint_commit],
        cwd=project_root,
        timeout_seconds=60,
    )

    if not result.passed:
        raise RuntimeError(
            f"Could not restore Git checkpoint {checkpoint_commit}."
        )

    clean_result = run_command(
        ["git", "clean", "-fd"],
        cwd=project_root,
        timeout_seconds=60,
    )

    if not clean_result.passed:
        raise RuntimeError(
            "Could not remove files created after the checkpoint."
        )


def git_get_changes_since_commit(project_root: Path, commit_hash: str) -> list[str]:
    """Get all changed files since a specific commit."""
    result = run_command(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
        cwd=project_root,
        timeout_seconds=30,
    )
    
    if not result.passed:
        return []
        
    return sorted(set(line.strip() for line in result.stdout.splitlines() if line.strip()))
