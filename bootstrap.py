from pathlib import Path
from .project_context import ProjectContext
from .project_loader import ProjectLoader

def bootstrap(project_root: Path):
    ctx = ProjectContext(project_root=project_root)
    loader = ProjectLoader(ctx)
    return loader.load_all()
