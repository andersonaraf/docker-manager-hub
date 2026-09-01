from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from docker_file_manager.services.docker_service import DockerService
from docker_file_manager.ui.main_window import MainWindow


def configure_logging() -> Path:
    log_dir = Path.home() / ".local" / "share" / "docker-file-manager" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "application.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )
    return log_file


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Docker File Manager")
    try:
        service = DockerService()
    except Exception as exc:
        QMessageBox.critical(None, "Docker File Manager", str(exc))
        return 1
    window = MainWindow(service)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

