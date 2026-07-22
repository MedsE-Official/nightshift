from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    FAILED = "failed"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TaskEvent:
    timestamp: datetime
    message: str


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    prompt: str
    files: tuple[Path, ...]
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    run_tests: bool = True
    events: tuple[TaskEvent, ...] = field(default_factory=tuple)

    @property
    def has_files(self) -> bool:
        return bool(self.files)


@dataclass(frozen=True)
class Feature:
    id: str
    title: str
    tasks: tuple[Task, ...]


@dataclass(frozen=True)
class Backlog:
    features: tuple[Feature, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Backlog":
        """Build the domain backlog from already loaded project data."""

        if not isinstance(data, dict):
            raise ValueError("Top-level JSON value must be an object")

        features_data = data.get("features", [])
        if not isinstance(features_data, list):
            raise ValueError("'features' must be an array")

        features = tuple(
            _parse_feature(feature_data, feature_index)
            for feature_index, feature_data in enumerate(features_data)
        )
        return cls(features=features)


    @property
    def tasks(self) -> tuple[Task, ...]:
        """Return every task in feature order and task order."""
        return tuple(
            task
            for feature in self.features
            for task in feature.tasks
        )


def _parse_feature(data: Any, index: int) -> Feature:
    if not isinstance(data, dict):
        raise ValueError(f"Feature at index {index} must be an object")

    feature_id = _required_string(data, "id", f"Feature at index {index}")
    title = _required_string(data, "title", f"Feature at index {index}")

    tasks_data = data.get("tasks", [])
    if not isinstance(tasks_data, list):
        raise ValueError(f"Feature at index {index} tasks must be an array")

    tasks = tuple(
        _parse_task(task_data, feature_index=index, task_index=task_index)
        for task_index, task_data in enumerate(tasks_data)
    )
    return Feature(id=feature_id, title=title, tasks=tasks)


def _parse_task(data: Any, *, feature_index: int, task_index: int) -> Task:
    context = f"Task at feature {feature_index}, index {task_index}"
    if not isinstance(data, dict):
        raise ValueError(f"{context} must be an object")

    status_value = data.get("status")
    if status_value is None:
        raise ValueError("Task must have a status")
    try:
        status = TaskStatus(status_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid task status: {status_value}") from exc

    files_data = data.get("files")
    if not isinstance(files_data, list):
        raise ValueError(f"{context} files must be an array")
    if not all(isinstance(file_name, str) for file_name in files_data):
        raise ValueError(f"{context} files must contain only strings")

    run_tests = data.get("run_tests", True)
    if not isinstance(run_tests, bool):
        raise ValueError(f"{context} run_tests must be a boolean")

    events_data = data.get("events", [])
    if not isinstance(events_data, list):
        raise ValueError(f"{context} events must be an array")

    fallback_timestamp = datetime.now(timezone.utc)

    return Task(
        id=_required_string(data, "id", context),
        title=_required_string(data, "title", context),
        prompt=_required_string(data, "prompt", context),
        files=tuple(Path(file_name) for file_name in files_data),
        status=status,
        created_at=_datetime_or_default(
            data,
            "created_at",
            default=fallback_timestamp,
        ),
        updated_at=_datetime_or_default(
            data,
            "updated_at",
            default=fallback_timestamp,
        ),
        run_tests=run_tests,
        events=tuple(
            _parse_event(event_data, context=context, event_index=event_index)
            for event_index, event_data in enumerate(events_data)
        ),
    )


def _parse_event(data: Any, *, context: str, event_index: int) -> TaskEvent:
    event_context = f"{context} event at index {event_index}"
    if not isinstance(data, dict):
        raise ValueError(f"{event_context} must be an object")

    return TaskEvent(
        timestamp=_required_datetime(data, "timestamp", event_context),
        message=_required_string(data, "message", event_context),
    )


def _required_string(data: dict[str, Any], field_name: str, context: str) -> str:
    if field_name not in data:
        raise ValueError(f"{context} missing required field '{field_name}'")
    value = data[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{context} {field_name} must be a string")
    return value



def _datetime_or_default(
    data: dict[str, Any],
    field_name: str,
    *,
    default: datetime,
) -> datetime:
    """Return an ISO datetime or a supplied fallback for missing/invalid values."""
    value = data.get(field_name)

    if not isinstance(value, str):
        return default

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return default

def _required_datetime(
    data: dict[str, Any], field_name: str, context: str
) -> datetime:
    value = _required_string(data, field_name, context)
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{context} {field_name} must be a valid ISO datetime"
        ) from exc