import json
import tempfile
import pytest
from dataclasses import FrozenInstanceError
from pathlib import Path
from planner import Planner, PlannerTask, load_backlog
from builder import BuilderTask


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


def test_load_backlog_single_task():
    """Test that one valid task loads correctly."""
    # Create a temporary backlog file
    backlog_data = [
        {
            "id": "task-1",
            "title": "Test Task",
            "prompt": "This is a test prompt",
            "files": ["file1.py", "file2.py"]
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        tasks = load_backlog(backlog_file)
        assert len(tasks) == 1
        assert tasks[0].id == "task-1"
        assert tasks[0].title == "Test Task"
        assert tasks[0].prompt == "This is a test prompt"
        assert tasks[0].files == (Path("file1.py"), Path("file2.py"))
    finally:
        backlog_file.unlink()


def test_load_backlog_multiple_tasks():
    """Test that multiple tasks preserve order."""
    backlog_data = [
        {
            "id": "task-1",
            "title": "First Task",
            "prompt": "First prompt",
            "files": ["file1.py"]
        },
        {
            "id": "task-2",
            "title": "Second Task",
            "prompt": "Second prompt",
            "files": ["file2.py"]
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        tasks = load_backlog(backlog_file)
        assert len(tasks) == 2
        assert tasks[0].id == "task-1"
        assert tasks[1].id == "task-2"
    finally:
        backlog_file.unlink()


def test_load_backlog_files_become_paths():
    """Test that file strings become Path objects."""
    backlog_data = [
        {
            "id": "task-1",
            "title": "Test Task",
            "prompt": "Test prompt",
            "files": ["file1.py", "subdir/file2.py"]
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        tasks = load_backlog(backlog_file)
        assert len(tasks) == 1
        assert isinstance(tasks[0].files[0], Path)
        assert isinstance(tasks[0].files[1], Path)
        assert str(tasks[0].files[0]) == "file1.py"
        assert str(tasks[0].files[1]) == "subdir/file2.py"
    finally:
        backlog_file.unlink()


def test_load_backlog_empty_backlog():
    """Test that an empty backlog returns an empty tuple."""
    backlog_data = []
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        tasks = load_backlog(backlog_file)
        assert len(tasks) == 0
    finally:
        backlog_file.unlink()


def test_load_backlog_malformed_json():
    """Test that malformed JSON raises json.JSONDecodeError."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"invalid": json}')
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(json.JSONDecodeError):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()


def test_load_backlog_top_level_not_array():
    """Test that non-array top-level JSON raises ValueError."""
    backlog_data = {
        "id": "task-1",
        "title": "Test Task",
        "prompt": "Test prompt",
        "files": ["file1.py"]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Top-level JSON value must be an array"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()


def test_load_backlog_task_not_object():
    """Test that non-object task items raise ValueError."""
    backlog_data = [
        "not-an-object",
        {
            "id": "task-1",
            "title": "Test Task",
            "prompt": "Test prompt",
            "files": ["file1.py"]
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Task at index 0 must be an object"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()


def test_load_backlog_missing_required_fields():
    """Test that missing required fields raise ValueError."""
    backlog_data = [
        {
            "id": "task-1",
            "title": "Test Task"
            # Missing prompt and files
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Task at index 0 missing required field 'prompt'"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()


def test_load_backlog_invalid_field_types():
    """Test that invalid field types raise ValueError."""
    # Test id not string
    backlog_data = [
        {
            "id": 123,
            "title": "Test Task",
            "prompt": "Test prompt",
            "files": ["file1.py"]
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Task at index 0 id must be a string"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()
    
    # Test title not string
    backlog_data[0]["id"] = "task-1"
    backlog_data[0]["title"] = 456
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Task at index 0 title must be a string"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()
    
    # Test prompt not string
    backlog_data[0]["title"] = "Test Task"
    backlog_data[0]["prompt"] = {"not": "a string"}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Task at index 0 prompt must be a string"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()


def test_load_backlog_files_not_array():
    """Test that non-array files raise ValueError."""
    backlog_data = [
        {
            "id": "task-1",
            "title": "Test Task",
            "prompt": "Test prompt",
            "files": "not-an-array"
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Task at index 0 files must be an array"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()


def test_load_backlog_files_not_strings():
    """Test that non-string file items raise ValueError."""
    backlog_data = [
        {
            "id": "task-1",
            "title": "Test Task",
            "prompt": "Test prompt",
            "files": ["file1.py", 123]
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(backlog_data, f)
        backlog_file = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Task at index 0 files must contain only strings"):
            load_backlog(backlog_file)
    finally:
        backlog_file.unlink()


def test_planner_initialization():
    """Test that Planner initializes correctly."""
    task1 = PlannerTask("task1", "Task 1", "Prompt 1", (Path("file1.py"),))
    task2 = PlannerTask("task2", "Task 2", "Prompt 2", (Path("file2.py"),))
    
    planner = Planner((task1, task2))
    assert planner.remaining == 2
    assert planner._index == 0


def test_planner_next_task():
    """Test that Planner.next_task() returns tasks in order."""
    task1 = PlannerTask("task1", "Task 1", "Prompt 1", (Path("file1.py"),))
    task2 = PlannerTask("task2", "Task 2", "Prompt 2", (Path("file2.py"),))
    
    planner = Planner((task1, task2))
    
    # First call should return first task
    assert planner.next_task() == task1
    assert planner.remaining == 1
    assert planner._index == 1
    
    # Second call should return second task
    assert planner.next_task() == task2
    assert planner.remaining == 0
    assert planner._index == 2
    
    # Third call should return None
    assert planner.next_task() is None
    assert planner.remaining == 0
    assert planner._index == 2


def test_planner_empty_tasks():
    """Test that Planner works with empty task list."""
    planner = Planner(())
    assert planner.remaining == 0
    assert planner.next_task() is None
    assert planner.remaining == 0


def test_planner_next_builder_task():
    """Test that Planner.next_builder_task() converts PlannerTask to BuilderTask."""
    # Create a PlannerTask
    planner_task = PlannerTask(
        id="task-1",
        title="Test Task",
        prompt="This is a test prompt",
        files=(Path("file1.py"), Path("file2.py"))
    )
    
    # Create a Planner with that task
    planner = Planner((planner_task,))
    
    # Get the BuilderTask
    builder_task = planner.next_builder_task()
    
    # Verify it's a BuilderTask
    assert isinstance(builder_task, BuilderTask)
    
    # Verify prompt is preserved
    assert builder_task.prompt == "This is a test prompt"
    
    # Verify files are preserved
    assert builder_task.files == (Path("file1.py"), Path("file2.py"))
    
    # Verify that calling it again returns None (exhausted)
    assert planner.next_builder_task() is None


def test_planner_next_builder_task_empty():
    """Test that Planner.next_builder_task() returns None when no tasks remain."""
    planner = Planner(())
    assert planner.next_builder_task() is None


def test_planner_remaining_property():
    """Test that Planner.remaining property works correctly."""
    task1 = PlannerTask("task1", "Task 1", "Prompt 1", (Path("file1.py"),))
    task2 = PlannerTask("task2", "Task 2", "Prompt 2", (Path("file2.py"),))
    
    planner = Planner((task1, task2))
    
    # Initially should have 2 remaining
    assert planner.remaining == 2
    
    # After one call should have 1 remaining
    planner.next_task()
    assert planner.remaining == 1
    
    # After two calls should have 0 remaining
    planner.next_task()
    assert planner.remaining == 0
    
    # After three calls should still have 0 remaining
    planner.next_task()
    assert planner.remaining == 0


def test_planner_current_task():
    """Test that Planner.current_task property works correctly."""
    task1 = PlannerTask("task1", "Task 1", "Prompt 1", (Path("file1.py"),))
    task2 = PlannerTask("task2", "Task 2", "Prompt 2", (Path("file2.py"),))
    
    planner = Planner((task1, task2))
    
    # Initially should be None
    assert planner.current_task is None
    
    # After first next_task() call, should return the first task
    first_task = planner.next_task()
    assert planner.current_task == first_task
    assert planner.current_task is task1
    
    # After second next_task() call, should return the second task
    second_task = planner.next_task()
    assert planner.current_task == second_task
    assert planner.current_task is task2
    
    # After exhaustion, should still return the last task
    assert planner.next_task() is None
    assert planner.current_task == second_task
    assert planner.current_task is task2


def test_planner_current_task_with_next_builder_task():
    """Test that Planner.current_task property works correctly with next_builder_task()."""
    task1 = PlannerTask("task1", "Task 1", "Prompt 1", (Path("file1.py"),))
    
    planner = Planner((task1,))
    
    # Initially should be None
    assert planner.current_task is None
    
    # After next_builder_task() call, should return the task that was processed
    builder_task = planner.next_builder_task()
    assert planner.current_task == task1
    
    # After exhaustion, should still return the last task
    assert planner.next_builder_task() is None
    assert planner.current_task == task1
