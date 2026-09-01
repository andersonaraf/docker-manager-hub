from __future__ import annotations

import json
from collections.abc import Iterable

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QLineEdit, QPushButton, QStyle, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from docker_file_manager.models import FileEntry

MIME_TYPE = "application/x-docker-file-manager-items"


class FileTree(QTreeWidget):
    items_dropped = Signal(str, list)

    def __init__(self, side: str) -> None:
        super().__init__()
        self.side = side
        self.setHeaderLabels(["Nome", "Tamanho", "Tipo", "Modificado"])
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSortingEnabled(True)

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        paths = [item.data(0, Qt.ItemDataRole.UserRole) for item in self.selectedItems()]
        if not paths:
            return
        mime = QMimeData()
        mime.setData(MIME_TYPE, json.dumps({"side": self.side, "paths": paths}).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        payload = json.loads(bytes(event.mimeData().data(MIME_TYPE)))
        if payload.get("side") != self.side:
            target = self.itemAt(event.position().toPoint())
            target_path = target.data(0, Qt.ItemDataRole.UserRole) if target and target.data(0, Qt.ItemDataRole.UserRole + 1) else ""
            self.items_dropped.emit(target_path, payload.get("paths", []))
            event.acceptProposedAction()


class BrowserBase(QWidget):
    path_submitted = Signal(str)

    def __init__(self, title: str, side: str) -> None:
        super().__init__()
        self.current_path = "/"
        self.back_stack: list[str] = []
        self.forward_stack: list[str] = []
        self.back_button = QPushButton("←")
        self.up_button = QPushButton("↑")
        self.refresh_button = QPushButton("↻")
        self.path_edit = QLineEdit()
        self.tree = FileTree(side)
        self.tree.itemDoubleClicked.connect(self._activate_item)
        self.path_edit.returnPressed.connect(lambda: self.navigate(self.path_edit.text()))
        self.back_button.clicked.connect(self.go_back)
        self.up_button.clicked.connect(self.go_up)
        self.refresh_button.clicked.connect(self.refresh)

        controls = QHBoxLayout()
        controls.addWidget(self.back_button)
        controls.addWidget(self.up_button)
        controls.addWidget(self.path_edit, 1)
        controls.addWidget(self.refresh_button)
        layout = QVBoxLayout(self)
        from PySide6.QtWidgets import QLabel
        label = QLabel(title)
        label.setStyleSheet("font-weight: 600; font-size: 14px")
        layout.addWidget(label)
        layout.addLayout(controls)
        layout.addWidget(self.tree, 1)

    def show_entries(self, entries: Iterable[FileEntry]) -> None:
        self.tree.clear()
        style = self.style()
        for entry in entries:
            modified = entry.modified.astimezone().strftime("%Y-%m-%d %H:%M") if entry.modified else "—"
            size = "—" if entry.is_dir else format_size(entry.size)
            item = QTreeWidgetItem([entry.name, size, entry.kind, modified])
            item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, entry.is_dir)
            icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon if entry.is_dir else QStyle.StandardPixmap.SP_FileIcon)
            item.setIcon(0, icon)
            self.tree.addTopLevelItem(item)
        self.path_edit.setText(self.current_path)
        self.tree.resizeColumnToContents(0)

    def navigate(self, path: str, remember: bool = True) -> None:
        raise NotImplementedError

    def refresh(self) -> None:
        self.navigate(self.current_path, remember=False)

    def go_back(self) -> None:
        if self.back_stack:
            target = self.back_stack.pop()
            self.navigate(target, remember=False)

    def go_up(self) -> None:
        raise NotImplementedError

    def _activate_item(self, item: QTreeWidgetItem) -> None:
        if item.data(0, Qt.ItemDataRole.UserRole + 1):
            self.navigate(item.data(0, Qt.ItemDataRole.UserRole))


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"

