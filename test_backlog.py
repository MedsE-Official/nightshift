from datetime import datetime
from pathlib import Path

import pytest

from backlog import Backlog, TaskStatus


def task_data(status: str = "pending"):
    return {
        "id": "task-1",
        "title": "Task 1",
        "prompt": "Implement task 1",
        "files": ["src/task.py"],
        "status": status,
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-02T00:00:00",
        "events": [],
    }


def test_backlog_builds_from_validated_dictionary():
    backlog = Backlog.from_dict({
        "schema_version": "1.0",
        "features": [{
            "id": "feature-1",
            "title": "Feature 1",
            "tasks": [task_data()],
        }],
    })

    assert backlog.tasks[0].id == "task-1"
    assert backlog.tasks[0].files == (Path("src/task.py"),)
    assert backlog.tasks[0].status is TaskStatus.PENDING
    assert backlog.tasks[0].created_at == datetime.fromisoformat(
        "2023-01-01T00:00:00"
    )


def test_backlog_rejects_invalid_status():
    with pytest.raises(ValueError, match="Invalid task status"):
        Backlog.from_dict({
            "features": [{
                "id": "feature-1",
                "title": "Feature 1",
                "tasks": [task_data("invalid")],
            }]
        })


def test_backlog_has_no_file_loading_api():
    assert not hasattr(Backlog, "from_json_file")


def test_task_run_tests_defaults_to_true():
    backlog = Backlog.from_dict({
        "schema_version": "1.0",
        "features": [{
            "id": "feature-1",
            "title": "Feature 1",
            "tasks": [task_data()],
        }],
    })

    assert backlog.tasks[0].run_tests is True


def test_task_run_tests_can_be_disabled():
    data = task_data()
    data["run_tests"] = False
    backlog = Backlog.from_dict({
        "schema_version": "1.0",
        "features": [{
            "id": "feature-1",
            "title": "Feature 1",
            "tasks": [data],
        }],
    })

    assert backlog.tasks[0].run_tests is False


def test_task_run_tests_must_be_boolean():
    data = task_data()
    data["run_tests"] = "false"

    with pytest.raises(ValueError, match="run_tests must be a boolean"):
        Backlog.from_dict({
            "schema_version": "1.0",
            "features": [{
                "id": "feature-1",
                "title": "Feature 1",
                "tasks": [data],
            }],
        })
