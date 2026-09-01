from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FileEntry:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    modified: datetime | None = None
    kind: str = "file"

