import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from backlog import Backlog, Feature, Task, TaskStatus
from builder import BuilderTask
from planner import Planner


NOW = datetime(2023, 1, 1)


def make_task(
    task_id: str,
    *,
    prompt: str | None = None,
    files: tuple[Path, ...] = (),
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        prompt=prompt or f"Prompt {task_id}",
        files=files,
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def make_backlog(*tasks: Task) -> Backlog:
    return Backlog(
        features=(Feature(id="feature-1", title="Feature 1", tasks=tasks),)
    )


def test_planner_accepts_backlog_and_preserves_task_order():
    first = make_task("first")
    second = make_task("second")
    planner = Planner(make_backlog(first, second))

    assert planner.remaining == 2
    assert planner.current_task is None

    assert planner.next_task() is first
    assert planner.remaining == 1
    assert planner.current_task is first

    assert planner.next_task() is second
    assert planner.remaining == 0
    assert planner.current_task is second

    assert planner.next_task() is None
    assert planner.remaining == 0
    assert planner.current_task is second


def test_planner_preserves_existing_behavior_for_all_statuses():
    pending = make_task("pending", status=TaskStatus.PENDING)
    done = make_task("done", status=TaskStatus.DONE)
    planner = Planner(make_backlog(pending, done))

    assert planner.next_task() is pending
    assert planner.next_task() is done
    assert planner.next_task() is None


def test_planner_handles_empty_backlog():
    planner = Planner(Backlog(features=()))

    assert planner.remaining == 0
    assert planner.current_task is None
    assert planner.next_task() is None
    assert planner.next_builder_task() is None


def test_next_builder_task_converts_domain_task():
    task = make_task(
        "task-1",
        prompt="Implement the example",
        files=(Path("example.py"), Path("test_example.py")),
    )
    planner = Planner(make_backlog(task))

    builder_task = planner.next_builder_task()

    assert isinstance(builder_task, BuilderTask)
    assert builder_task == BuilderTask(
        prompt="Implement the example",
        files=(Path("example.py"), Path("test_example.py")),
    )
    assert planner.current_task is task
    assert planner.next_builder_task() is None


def test_planner_flattens_tasks_across_features():
    first = make_task("first")
    second = make_task("second")
    backlog = Backlog(
        features=(
            Feature("feature-1", "Feature 1", (first,)),
            Feature("feature-2", "Feature 2", (second,)),
        )
    )
    planner = Planner(backlog)

    assert planner.next_task() is first
    assert planner.next_task() is second


def test_from_backlog_delegates_file_loading_to_backlog(tmp_path):
    backlog_file = tmp_path / "backlog.json"
    backlog = make_backlog(make_task("task-1"))

    with patch(
        "planner.Backlog.from_json_file",
        return_value=backlog,
    ) as from_json_file:
        planner = Planner.from_backlog(backlog_file)

    from_json_file.assert_called_once_with(backlog_file)
    assert planner.next_task() is backlog.tasks[0]


def test_from_backlog_loads_real_json_file(tmp_path):
    backlog_file = tmp_path / "backlog.json"
    backlog_file.write_text(
        json.dumps(
            {
                "features": [
                    {
                        "id": "feature-1",
                        "title": "Feature 1",
                        "tasks": [
                            {
                                "id": "task-1",
                                "title": "Task 1",
                                "prompt": "Implement task 1",
                                "files": ["task.py"],
                                "status": "pending",
                                "created_at": "2023-01-01T00:00:00",
                                "updated_at": "2023-01-01T00:00:00",
                                "events": [],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    planner = Planner.from_backlog(backlog_file)

    builder_task = planner.next_builder_task()
    assert builder_task == BuilderTask(
        prompt="Implement task 1",
        files=(Path("task.py"),),
    )
