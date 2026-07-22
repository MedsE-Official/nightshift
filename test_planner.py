from pathlib import Path
from types import SimpleNamespace

from builder import BuilderTask
from planner import Planner


def configuration_with_tasks(*tasks):
    return SimpleNamespace(
        backlog={
            "schema_version": "1.0",
            "features": [{
                "id": "feature",
                "title": "Feature",
                "tasks": list(tasks),
            }],
        }
    )


def task(task_id: str, status: str):
    return {
        "id": task_id,
        "title": task_id,
        "prompt": f"Prompt {task_id}",
        "files": [f"{task_id}.py"],
        "status": status,
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00",
        "events": [],
    }


def test_planner_is_created_from_configuration_and_selects_pending_tasks():
    configuration = configuration_with_tasks(
        task("done", "done"),
        task("pending", "pending"),
    )

    planner = Planner.from_configuration(configuration)

    assert planner.next_builder_task() == BuilderTask(
        prompt="Prompt pending",
        files=(Path("pending.py"),),
    )
    assert planner.next_builder_task() is None


def test_planner_propagates_run_tests_false_to_builder_task():
    disabled_task = task("pending", "pending")
    disabled_task["run_tests"] = False
    planner = Planner.from_configuration(
        configuration_with_tasks(disabled_task)
    )

    assert planner.next_builder_task() == BuilderTask(
        prompt="Prompt pending",
        files=(Path("pending.py"),),
        run_tests=False,
    )


def test_complete_current_task_persists_done_status(tmp_path):
    import json
    from types import SimpleNamespace

    backlog_file = tmp_path / ".nightshift" / "backlog.json"
    backlog_file.parent.mkdir()
    pending_task = task("pending", "pending")
    original_updated_at = pending_task["updated_at"]
    backlog_data = {
        "schema_version": "1.0",
        "features": [{
            "id": "feature",
            "title": "Feature",
            "tasks": [pending_task],
        }],
    }
    backlog_file.write_text(json.dumps(backlog_data), encoding="utf-8")
    configuration = SimpleNamespace(
        backlog=backlog_data,
        context=SimpleNamespace(backlog_file=backlog_file),
    )
    planner = Planner.from_configuration(configuration)

    planner.next_builder_task()
    planner.complete_current_task()

    persisted = json.loads(backlog_file.read_text(encoding="utf-8"))
    completed = persisted["features"][0]["tasks"][0]
    assert completed["status"] == "done"
    assert completed["updated_at"] != original_updated_at
    assert completed["events"][-1]["message"] == (
        "Task completed after approved Nightshift cycle."
    )


def test_complete_current_task_requires_selected_task():
    planner = Planner.from_configuration(
        configuration_with_tasks(task("pending", "pending"))
    )

    import pytest
    with pytest.raises(RuntimeError, match="No current task"):
        planner.complete_current_task()
