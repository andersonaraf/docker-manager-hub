from __future__ import annotations

import posixpath
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Signal

from docker_file_manager.services.container_filesystem import ContainerFileSystem
from docker_file_manager.ui.browser_base import BrowserBase


class ContainerBrowser(BrowserBase):
    host_items_dropped = Signal(str, list)
    error = Signal(str)

    def __init__(self, filesystem: ContainerFileSystem) -> None:
        super().__init__("CONTAINER", "container")
        self.filesystem = filesystem
        self.container_provider: Callable[[], Any | None] = lambda: None
        self.tree.items_dropped.connect(self._drop)

    def navigate(self, path: str, remember: bool = True) -> None:
        container = self.container_provider()
        if container is None:
            self.tree.clear()
            return
        target = self.filesystem.normalize(path)
        try:
            entries = self.filesystem.list_directory(container, target)
        except Exception as exc:
            self.error.emit(str(exc))
            return
        if remember and target != self.current_path:
            self.back_stack.append(self.current_path)
        self.current_path = target
        self.show_entries(entries)

    def go_up(self) -> None:
        self.navigate(posixpath.dirname(self.current_path) or "/")

    def _drop(self, target: str, paths: list[str]) -> None:
        self.host_items_dropped.emit(target or self.current_path, paths)

