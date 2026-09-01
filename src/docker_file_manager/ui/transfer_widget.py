from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from docker_file_manager.ui.browser_base import format_size


class TransferWidget(QWidget):
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.label = QLabel("Pronto")
        self.details = QLabel("")
        self.progress = QProgressBar()
        self.cancel = QPushButton("Cancelar")
        self.cancel.clicked.connect(self.cancel_requested)
        row = QHBoxLayout()
        row.addWidget(self.progress, 1)
        row.addWidget(self.cancel)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(row)
        layout.addWidget(self.details)
        self.set_idle()

    def update_progress(self, done: int, total: int | None, name: str, speed: float) -> None:
        self.label.setText(f"Copiando {name}")
        self.cancel.setEnabled(True)
        if total:
            self.progress.setRange(0, 100)
            self.progress.setValue(min(100, int(done * 100 / total)))
            amount = f"{format_size(done)} / {format_size(total)}"
        else:
            self.progress.setRange(0, 0)
            amount = format_size(done)
        self.details.setText(f"{amount} — {format_size(int(speed))}/s")

    def set_idle(self, message: str = "Pronto") -> None:
        self.label.setText(message)
        self.details.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.cancel.setEnabled(False)

