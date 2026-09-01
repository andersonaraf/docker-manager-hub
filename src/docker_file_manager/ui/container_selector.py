from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox

from docker_file_manager.models import ContainerInfo


class ContainerSelector(QComboBox):
    container_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.currentIndexChanged.connect(self._selected)

    def set_containers(self, containers: list[ContainerInfo]) -> None:
        self.blockSignals(True)
        self.clear()
        for container in containers:
            marker = "●" if container.is_running else "○"
            self.addItem(f"{marker} {container.name} — {container.image} ({container.status})", container.id)
        self.blockSignals(False)
        if self.count():
            self.setCurrentIndex(0)
            self.container_selected.emit(self.currentData())

    def _selected(self, index: int) -> None:
        if index >= 0:
            self.container_selected.emit(self.itemData(index))

