import pytest
from dataclasses import FrozenInstanceError
from pathlib import Path
from planner import PlannerTask


def test_planner_task_attributes():
    """Test that PlannerTask stores all required attributes correctly."""
    task = PlannerTask(
        id="task-1",
        title="Test Task",
        prompt="This is a test prompt",
        files=(Path("file1.py"), Path("file2.py"))
    )
    
    assert task.id == "task-1"
    assert task.title == "Test Task"
    assert task.prompt == "This is a test prompt"
    assert task.files == (Path("file1.py"), Path("file2.py"))


def test_planner_task_has_files():
    """Test that has_files property works correctly."""
    # Test with non-empty files tuple
    task_with_files = PlannerTask(
        id="task-1",
        title="Test Task",
        prompt="This is a test prompt",
        files=(Path("file1.py"), Path("file2.py"))
    )
    assert task_with_files.has_files is True
    
    # Test with empty files tuple
    task_without_files = PlannerTask(
        id="task-2",
        title="Test Task 2",
        prompt="This is another test prompt",
        files=()
    )
    assert task_without_files.has_files is False


def test_planner_task_immutable():
    """Test that PlannerTask is immutable."""
    task = PlannerTask(
        id="task-1",
        title="Test Task",
        prompt="This is a test prompt",
        files=(Path("file1.py"),)
    )
    
    # Attempt to modify the task (should raise FrozenInstanceError)
    with pytest.raises(FrozenInstanceError):
        task.id = "new-id"
    
    with pytest.raises(FrozenInstanceError):
        task.title = "New Title"
    
    with pytest.raises(FrozenInstanceError):
        task.prompt = "New prompt"
    
    with pytest.raises(FrozenInstanceError):
        task.files = ()
