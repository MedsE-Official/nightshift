import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlannerTask:
    id: str
    title: str
    prompt: str
    files: tuple[Path, ...]

    @property
    def has_files(self) -> bool:
        return len(self.files) > 0


def load_backlog(backlog_file: Path) -> tuple[PlannerTask, ...]:
    """Load PlannerTask objects from a JSON backlog file.
    
    Args:
        backlog_file: Path to the JSON backlog file
        
    Returns:
        Tuple of PlannerTask objects in the same order as in the JSON array
        
    Raises:
        ValueError: For any invalid structure in the backlog
        json.JSONDecodeError: For malformed JSON
    """
    with open(backlog_file, 'r') as f:
        data = json.load(f)
    
    # Check that top-level value is an array
    if not isinstance(data, list):
        raise ValueError("Top-level JSON value must be an array")
    
    tasks = []
    for i, item in enumerate(data):
        # Check that each item is an object
        if not isinstance(item, dict):
            raise ValueError(f"Task at index {i} must be an object")
        
        # Check required fields
        required_fields = ['id', 'title', 'prompt', 'files']
        for field in required_fields:
            if field not in item:
                raise ValueError(f"Task at index {i} missing required field '{field}'")
        
        # Validate field types
        if not isinstance(item['id'], str):
            raise ValueError(f"Task at index {i} id must be a string")
        
        if not isinstance(item['title'], str):
            raise ValueError(f"Task at index {i} title must be a string")
        
        if not isinstance(item['prompt'], str):
            raise ValueError(f"Task at index {i} prompt must be a string")
        
        if not isinstance(item['files'], list):
            raise ValueError(f"Task at index {i} files must be an array")
        
        # Convert files to Path objects
        try:
            files = tuple(Path(f) for f in item['files'])
        except TypeError:
            raise ValueError(f"Task at index {i} files must contain only strings")
        
        task = PlannerTask(
            id=item['id'],
            title=item['title'],
            prompt=item['prompt'],
            files=files
        )
        tasks.append(task)
    
    return tuple(tasks)
