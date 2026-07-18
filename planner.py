from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from backlog import Backlog, Task
from builder import BuilderTask

if TYPE_CHECKING:
    from configuration import Configuration


class Planner:
    def __init__(self, backlog: Backlog):
        self._tasks = backlog.tasks
        self._index = 0
        self._current_task: Task | None = None

    @classmethod
    def from_configuration(cls, configuration: "Configuration") -> "Planner":
        """Create a planner from validated project data."""

        return cls(Backlog.from_dict(configuration.backlog))

    @classmethod
    def from_backlog(cls, backlog_file: Path) -> "Planner":
        """Create a planner from a persisted backlog.

        File loading belongs to the Backlog model; Planner itself consumes the
        resulting Backlog object.
        """
        return cls(Backlog.from_json_file(backlog_file))

    def next_task(self) -> Task | None:
        if self._index >= len(self._tasks):
            return None

        task = self._tasks[self._index]
        self._index += 1
        self._current_task = task
        return task

    def next_builder_task(self) -> BuilderTask | None:
        task = self.next_task()
        if task is None:
            return None

        return BuilderTask(prompt=task.prompt, files=task.files)

    @property
    def current_task(self) -> Task | None:
        return self._current_task

    @property
    def remaining(self) -> int:
        return len(self._tasks) - self._index
