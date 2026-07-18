from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
from typing import List, Optional


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
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    events: List[TaskEvent] = field(default_factory=list)


@dataclass(frozen=True)
class Feature:
    id: str
    title: str
    tasks: List[Task]


@dataclass(frozen=True)
class Backlog:
    features: List[Feature]

    @classmethod
    def from_json_file(cls, path: Path) -> "Backlog":
        with open(path, 'r') as f:
            data = json.load(f)
        
        features = []
        for feature_data in data.get('features', []):
            tasks = []
            for task_data in feature_data.get('tasks', []):
                # Validate status
                status_str = task_data.get('status')
                if status_str is None:
                    raise ValueError("Task must have a status")
                
                try:
                    status = TaskStatus(status_str)
                except ValueError:
                    raise ValueError(f"Invalid task status: {status_str}")
                
                # Parse datetime fields
                created_at = datetime.fromisoformat(task_data['created_at'])
                updated_at = datetime.fromisoformat(task_data['updated_at'])
                
                # Parse events
                events = []
                for event_data in task_data.get('events', []):
                    timestamp = datetime.fromisoformat(event_data['timestamp'])
                    events.append(TaskEvent(timestamp=timestamp, message=event_data['message']))
                
                tasks.append(Task(
                    id=task_data['id'],
                    title=task_data['title'],
                    status=status,
                    created_at=created_at,
                    updated_at=updated_at,
                    events=events
                ))
            
            features.append(Feature(
                id=feature_data['id'],
                title=feature_data['title'],
                tasks=tasks
            ))
        
        return cls(features=features)
