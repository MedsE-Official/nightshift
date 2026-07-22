from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backlog import Backlog, Task
from builder import BuilderTask
from configuration import Configuration


class Planner:
    def __init__(self, *, configuration: Configuration, backlog: Backlog):
        self.configuration = configuration
        self._tasks = backlog.tasks
        self._index = 0
        self._current_task: Task | None = None

    @classmethod
    def from_configuration(cls, configuration: Configuration) -> "Planner":
        return cls(
            configuration=configuration,
            backlog=Backlog.from_dict(configuration.backlog),
        )

    def next_task(self) -> Task | None:
        while self._index < len(self._tasks):
            task = self._tasks[self._index]
            self._index += 1
            if task.status.value == "pending":
                self._current_task = task
                return task
        return None

    def next_builder_task(self) -> BuilderTask | None:
        task = self.next_task()
        if task is None:
            return None
        return BuilderTask(
            prompt=task.prompt,
            files=task.files,
            run_tests=task.run_tests,
        )


    def complete_current_task(self) -> None:
        """Persist the current task as done in the project backlog."""
        if self._current_task is None:
            raise RuntimeError("No current task is available to complete")

        backlog_data = self.configuration.backlog
        completed_at = datetime.now(timezone.utc).isoformat()
        matching_tasks: list[dict[str, object]] = []

        for feature in backlog_data.get("features", []):
            for task_data in feature.get("tasks", []):
                if task_data.get("id") == self._current_task.id:
                    matching_tasks.append(task_data)

        if not matching_tasks:
            raise RuntimeError(
                f"Current task {self._current_task.id!r} was not found in backlog"
            )
        if len(matching_tasks) > 1:
            raise RuntimeError(
                f"Task id {self._current_task.id!r} is not unique in backlog"
            )

        task_data = matching_tasks[0]
        task_data["status"] = "done"
        task_data["updated_at"] = completed_at
        events = task_data.setdefault("events", [])
        events.append({
            "timestamp": completed_at,
            "message": "Task completed after approved Nightshift cycle.",
        })

        backlog_file = Path(self.configuration.context.backlog_file)
        temporary_file = backlog_file.with_suffix(backlog_file.suffix + ".tmp")
        try:
            temporary_file.write_text(
                json.dumps(backlog_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary_file.replace(backlog_file)
        except OSError:
            temporary_file.unlink(missing_ok=True)
            raise

    @property
    def current_task(self) -> Task | None:
        return self._current_task

    @property
    def remaining(self) -> int:
        return sum(
            task.status.value == "pending"
            for task in self._tasks[self._index:]
        )
