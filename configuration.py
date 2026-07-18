from dataclasses import dataclass
from .project_context import ProjectContext
from .project_loader import ProjectLoader

@dataclass(frozen=True)
class Configuration:
    project: dict
    backlog: dict
    knowledge: dict
    adr: dict

    @classmethod
    def load(cls, project_root):
        context=ProjectContext(project_root=project_root)
        loader=ProjectLoader(context)
        data=loader.load_all()
        return cls(project=data.get("project",{}), backlog=data.get("backlog",{}), knowledge=data.get("knowledge",{}), adr=data.get("adr",{}))
