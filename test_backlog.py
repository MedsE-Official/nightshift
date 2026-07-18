import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
import pytest

from backlog import Backlog, Feature, Task, TaskStatus, TaskEvent


def test_backlog_from_json_file_valid():
    # Create a valid backlog JSON structure
    backlog_data = {
        "features": [
            {
                "id": "feature-1",
                "title": "Feature 1",
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Task 1",
                        "status": "pending",
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                        "events": [
                            {
                                "timestamp": "2023-01-01T00:00:00",
                                "message": "Task created"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # Write to temporary file
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        temp_file_path = Path(f.name)
    
    # Load backlog from file
    backlog = Backlog.from_json_file(temp_file_path)
    
    # Verify structure
    assert len(backlog.features) == 1
    feature = backlog.features[0]
    assert feature.id == "feature-1"
    assert feature.title == "Feature 1"
    assert len(feature.tasks) == 1
    task = feature.tasks[0]
    assert task.id == "task-1"
    assert task.title == "Task 1"
    assert task.status == TaskStatus.PENDING
    assert task.created_at == datetime(2023, 1, 1, 0, 0, 0)
    assert task.updated_at == datetime(2023, 1, 1, 0, 0, 0)
    assert len(task.events) == 1
    assert task.events[0].timestamp == datetime(2023, 1, 1, 0, 0, 0)
    assert task.events[0].message == "Task created"


def test_backlog_from_json_file_invalid_status():
    # Create a backlog JSON with invalid status
    backlog_data = {
        "features": [
            {
                "id": "feature-1",
                "title": "Feature 1",
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Task 1",
                        "status": "invalid_status",
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                        "events": []
                    }
                ]
            }
        ]
    }
    
    # Write to temporary file
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        temp_file_path = Path(f.name)
    
    # Should raise ValueError for invalid status
    with pytest.raises(ValueError, match="Invalid task status: invalid_status"):
        Backlog.from_json_file(temp_file_path)


def test_backlog_from_json_file_missing_status():
    # Create a backlog JSON with missing status
    backlog_data = {
        "features": [
            {
                "id": "feature-1",
                "title": "Feature 1",
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Task 1",
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                        "events": []
                    }
                ]
            }
        ]
    }
    
    # Write to temporary file
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        temp_file_path = Path(f.name)
    
    # Should raise ValueError for missing status
    with pytest.raises(ValueError, match="Task must have a status"):
        Backlog.from_json_file(temp_file_path)


def test_backlog_from_json_file_all_valid_statuses():
    # Test all valid statuses
    valid_statuses = [
        "pending",
        "in_progress", 
        "blocked",
        "failed",
        "done",
        "cancelled"
    ]
    
    for status in valid_statuses:
        backlog_data = {
            "features": [
                {
                    "id": "feature-1",
                    "title": "Feature 1",
                    "tasks": [
                        {
                            "id": "task-1",
                            "title": "Task 1",
                            "status": status,
                            "created_at": "2023-01-01T00:00:00",
                            "updated_at": "2023-01-01T00:00:00",
                            "events": []
                        }
                    ]
                }
            ]
        }
        
        # Write to temporary file
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(backlog_data, f)
            temp_file_path = Path(f.name)
        
        # Should not raise any exception
        backlog = Backlog.from_json_file(temp_file_path)
        assert backlog.features[0].tasks[0].status.value == status
