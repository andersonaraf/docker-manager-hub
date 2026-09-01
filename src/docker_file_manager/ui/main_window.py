from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget

from docker_file_manager.services.container_filesystem import ContainerFileSystem
from docker_file_manager.services.docker_service import DockerService
from docker_file_manager.services.transfer_service import TransferService
from docker_file_manager.ui.container_browser import ContainerBrowser
from docker_file_manager.ui.container_selector import ContainerSelector
from docker_file_manager.ui.host_browser import HostBrowser
from docker_file_manager.ui.transfer_widget import TransferWidget
from docker_file_manager.workers import TransferWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, docker_service: DockerService) -> None:
        super().__init__()
        self.setWindowTitle("Docker File Manager")
        self.resize(1400, 820)
        self.docker_service = docker_service
        self.filesystem = ContainerFileSystem()
        self.transfer_service = TransferService()
        self.thread_pool = QThreadPool.globalInstance()
        self.container: Any | None = None
        self.active_worker: TransferWorker | None = None

        self.selector = ContainerSelector()
        self.host_browser = HostBrowser()
        self.container_browser = ContainerBrowser(self.filesystem)
        self.container_browser.container_provider = lambda: self.container
        self.transfer_widget = TransferWidget()
        self.upload_button = QPushButton("Enviar →")
        self.download_button = QPushButton("← Baixar")

        header = QHBoxLayout()
        header.addWidget(self.selector, 1)
        header.addWidget(self.download_button)
        header.addWidget(self.upload_button)
        splitter = QSplitter()
        splitter.addWidget(self.host_browser)
        splitter.addWidget(self.container_browser)
        splitter.setSizes([700, 700])
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.transfer_widget)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.selector.container_selected.connect(self.select_container)
        self.host_browser.container_items_dropped.connect(self.download)
        self.container_browser.host_items_dropped.connect(self.upload)
        self.container_browser.error.connect(self.show_error)
        self.transfer_widget.cancel_requested.connect(self.cancel_transfer)
        self.upload_button.clicked.connect(self.upload_selected)
        self.download_button.clicked.connect(self.download_selected)
        self.reload_containers()

    def reload_containers(self) -> None:
        try:
            self.docker_service.ping()
            containers = self.docker_service.list_containers()
            self.selector.set_containers(containers)
            if not containers:
                self.statusBar().showMessage("Nenhum container encontrado")
        except Exception as exc:
            self.show_error(str(exc))

    def select_container(self, container_id: str) -> None:
        try:
            self.container = self.docker_service.get_container(container_id)
            self.container_browser.back_stack.clear()
            self.container_browser.navigate("/", remember=False)
            self.statusBar().showMessage(f"Container: {self.container.name}")
        except Exception as exc:
            self.show_error(str(exc))

    def upload_selected(self) -> None:
        paths = self._selected_paths(self.host_browser.tree)
        if paths:
            self.upload(self.container_browser.current_path, paths)

    def download_selected(self) -> None:
        paths = self._selected_paths(self.container_browser.tree)
        if paths:
            self.download(self.host_browser.current_path, paths)

    def upload(self, destination: str, paths: list[str]) -> None:
        if self.container is None:
            self.show_error("Selecione um container.")
            return
        self._start_transfer(self.transfer_service.upload, self.container, [Path(path) for path in paths], destination)

    def download(self, destination: str, paths: list[str]) -> None:
        if self.container is None:
            self.show_error("Selecione um container.")
            return
        self._start_transfer(self.transfer_service.download, self.container, paths, Path(destination))

    def _start_transfer(self, operation, *args) -> None:  # type: ignore[no-untyped-def]
        if self.active_worker is not None:
            self.show_error("Aguarde ou cancele a transferência atual.")
            return
        worker = TransferWorker(operation, *args)
        worker.signals.progress.connect(self.transfer_widget.update_progress)
        worker.signals.error.connect(self._transfer_error)
        worker.signals.finished.connect(lambda: self._transfer_done("Transferência concluída"))
        worker.signals.cancelled.connect(lambda: self._transfer_done("Transferência cancelada"))
        self.active_worker = worker
        self.thread_pool.start(worker)

    def cancel_transfer(self) -> None:
        if self.active_worker:
            self.active_worker.cancel()
            self.transfer_widget.label.setText("Cancelando…")

    def _transfer_done(self, message: str) -> None:
        self.active_worker = None
        self.transfer_widget.set_idle(message)
        self.host_browser.refresh()
        self.container_browser.refresh()

    def _transfer_error(self, message: str) -> None:
        logger.warning("Transfer failed: %s", message)
        self.active_worker = None
        self.transfer_widget.set_idle("Falha na transferência")
        self.show_error(message)

    def show_error(self, message: str) -> None:
        logger.warning("UI error: %s", message)
        self.statusBar().showMessage(message, 10000)
        QMessageBox.warning(self, "Docker File Manager", message)

    @staticmethod
    def _selected_paths(tree) -> list[str]:  # type: ignore[no-untyped-def]
        from PySide6.QtCore import Qt
        return [item.data(0, Qt.ItemDataRole.UserRole) for item in tree.selectedItems()]

