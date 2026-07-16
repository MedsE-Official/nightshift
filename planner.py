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
