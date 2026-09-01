from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Signal

from docker_file_manager.models import FileEntry
from docker_file_manager.ui.browser_base import BrowserBase


class HostBrowser(BrowserBase):
    container_items_dropped = Signal(str, list)

    def __init__(self) -> None:
        super().__init__("HOST", "host")
        self.tree.items_dropped.connect(self._drop)
        self.navigate(str(Path.home()), remember=False)

    def navigate(self, path: str, remember: bool = True) -> None:
        target = Path(path).expanduser().resolve()
        if not target.is_dir():
            raise NotADirectoryError(str(target))
        if remember and target != Path(self.current_path):
            self.back_stack.append(self.current_path)
        entries = []
        with os.scandir(target) as iterator:
            for item in iterator:
                try:
                    stat = item.stat(follow_symlinks=False)
                except OSError:
                    continue
                is_dir = item.is_dir(follow_symlinks=False)
                kind = "symlink" if item.is_symlink() else ("directory" if is_dir else "file")
                entries.append(FileEntry(item.name, item.path, is_dir, stat.st_size, datetime.fromtimestamp(stat.st_mtime, timezone.utc), kind))
        self.current_path = str(target)
        self.show_entries(sorted(entries, key=lambda entry: (not entry.is_dir, entry.name.casefold())))

    def go_up(self) -> None:
        self.navigate(str(Path(self.current_path).parent))

    def _drop(self, target: str, paths: list[str]) -> None:
        self.container_items_dropped.emit(target or self.current_path, paths)

