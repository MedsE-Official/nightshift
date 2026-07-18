import json
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from backlog import Backlog, Feature, Task, TaskEvent, TaskStatus


CREATED_AT = "2023-01-01T00:00:00"
UPDATED_AT = "2023-01-02T00:00:00"


def task_data(**overrides):
    data = {
        "id": "task-1",
        "title": "Task 1",
        "prompt": "Implement task 1",
        "files": ["src/task.py", "test_task.py"],
        "status": "pending",
        "created_at": CREATED_AT,
        "updated_at": UPDATED_AT,
        "events": [
            {
                "timestamp": CREATED_AT,
                "message": "Task created",
            }
        ],
    }
    data.update(overrides)
    return data


def backlog_data(*tasks):
    return {
        "features": [
            {
                "id": "feature-1",
                "title": "Feature 1",
                "tasks": list(tasks),
            }
        ]
    }


def write_json(tmp_path: Path, data) -> Path:
    path = tmp_path / "backlog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_backlog_from_json_file_loads_complete_domain_model(tmp_path):
    path = write_json(tmp_path, backlog_data(task_data()))

    backlog = Backlog.from_json_file(path)

    assert backlog == Backlog(
        features=(
            Feature(
                id="feature-1",
                title="Feature 1",
                tasks=(
                    Task(
                        id="task-1",
                        title="Task 1",
                        prompt="Implement task 1",
                        files=(Path("src/task.py"), Path("test_task.py")),
                        status=TaskStatus.PENDING,
                        created_at=datetime.fromisoformat(CREATED_AT),
                        updated_at=datetime.fromisoformat(UPDATED_AT),
                        events=(
                            TaskEvent(
                                timestamp=datetime.fromisoformat(CREATED_AT),
                                message="Task created",
                            ),
                        ),
                    ),
                ),
            ),
        )
    )


def test_backlog_collections_are_immutable_tuples(tmp_path):
    backlog = Backlog.from_json_file(
        write_json(tmp_path, backlog_data(task_data()))
    )

    assert isinstance(backlog.features, tuple)
    assert isinstance(backlog.features[0].tasks, tuple)
    assert isinstance(backlog.features[0].tasks[0].files, tuple)
    assert isinstance(backlog.features[0].tasks[0].events, tuple)

    with pytest.raises(FrozenInstanceError):
        backlog.features = ()


def test_task_has_files():
    common = {
        "id": "task-1",
        "title": "Task 1",
        "prompt": "Prompt",
        "status": TaskStatus.PENDING,
        "created_at": datetime.fromisoformat(CREATED_AT),
        "updated_at": datetime.fromisoformat(UPDATED_AT),
    }

    assert Task(files=(Path("file.py"),), **common).has_files is True
    assert Task(files=(), **common).has_files is False


def test_backlog_tasks_flattens_features_in_order():
    now = datetime.fromisoformat(CREATED_AT)

    def make_task(task_id: str) -> Task:
        return Task(
            id=task_id,
            title=task_id,
            prompt=task_id,
            files=(),
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

    first = make_task("first")
    second = make_task("second")
    third = make_task("third")
    backlog = Backlog(
        features=(
            Feature("feature-1", "Feature 1", (first, second)),
            Feature("feature-2", "Feature 2", (third,)),
        )
    )

    assert backlog.tasks == (first, second, third)


@pytest.mark.parametrize("status", list(TaskStatus))
def test_backlog_accepts_all_task_statuses(tmp_path, status):
    path = write_json(
        tmp_path,
        backlog_data(task_data(status=status.value)),
    )

    backlog = Backlog.from_json_file(path)

    assert backlog.tasks[0].status is status


def test_backlog_rejects_invalid_status(tmp_path):
    path = write_json(
        tmp_path,
        backlog_data(task_data(status="invalid_status")),
    )

    with pytest.raises(ValueError, match="Invalid task status: invalid_status"):
        Backlog.from_json_file(path)


def test_backlog_rejects_missing_status(tmp_path):
    data = task_data()
    del data["status"]
    path = write_json(tmp_path, backlog_data(data))

    with pytest.raises(ValueError, match="Task must have a status"):
        Backlog.from_json_file(path)


@pytest.mark.parametrize("field", ["id", "title", "prompt", "created_at", "updated_at"])
def test_backlog_rejects_missing_required_task_fields(tmp_path, field):
    data = task_data()
    del data[field]
    path = write_json(tmp_path, backlog_data(data))

    with pytest.raises(ValueError, match=f"missing required field '{field}'"):
        Backlog.from_json_file(path)


def test_backlog_rejects_non_array_files(tmp_path):
    path = write_json(
        tmp_path,
        backlog_data(task_data(files="src/task.py")),
    )

    with pytest.raises(ValueError, match="files must be an array"):
        Backlog.from_json_file(path)


def test_backlog_rejects_non_string_file_entries(tmp_path):
    path = write_json(
        tmp_path,
        backlog_data(task_data(files=["src/task.py", 123])),
    )

    with pytest.raises(ValueError, match="files must contain only strings"):
        Backlog.from_json_file(path)


def test_backlog_rejects_malformed_json(tmp_path):
    path = tmp_path / "backlog.json"
    path.write_text('{"invalid": json}', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        Backlog.from_json_file(path)
