from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progress = Signal(int, object, str, float)
    error = Signal(str)
    finished = Signal()
    cancelled = Signal()


class TransferWorker(QRunnable):
    def __init__(self, operation: Callable[..., None], *args: Any) -> None:
        super().__init__()
        self.operation = operation
        self.args = args
        self.signals = WorkerSignals()
        self._cancelled = False
        self._started = 0.0

    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        self._started = time.monotonic()
        try:
            self.operation(*self.args, self._report, lambda: self._cancelled)
        except Exception as exc:
            if self._cancelled:
                self.signals.cancelled.emit()
            else:
                self.signals.error.emit(str(exc))
        else:
            self.signals.finished.emit()

    def _report(self, transferred: int, total: int | None, name: str) -> None:
        elapsed = max(time.monotonic() - self._started, 0.001)
        self.signals.progress.emit(transferred, total, name, transferred / elapsed)

