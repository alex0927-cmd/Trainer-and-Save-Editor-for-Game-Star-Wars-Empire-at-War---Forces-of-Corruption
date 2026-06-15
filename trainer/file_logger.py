from __future__ import annotations

import sys
import threading
from datetime import datetime
from pathlib import Path

LOG_FILENAME = "trainer.log"


def trainer_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


class SessionFileLogger:
    """Дописує події сесії у файл поруч із трейнером."""

    def __init__(self) -> None:
        self.enabled = False
        self.path = trainer_root() / LOG_FILENAME
        self._lock = threading.Lock()
        self._fp = None

    def set_enabled(self, on: bool) -> Path:
        with self._lock:
            if on and not self.enabled:
                self.enabled = True
                self._fp = open(self.path, "a", encoding="utf-8")
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._write_raw("=" * 72)
                self._write_raw(f"Сесія розпочата: {stamp}")
                self._write_raw(f"Файл: {self.path}")
                self._write_raw("=" * 72)
            elif not on and self.enabled:
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._write_raw(f"Сесія завершена: {stamp}")
                self._write_raw("=" * 72)
                if self._fp:
                    self._fp.close()
                    self._fp = None
                self.enabled = False
        return self.path

    def write(self, message: str, category: str = "LOG") -> None:
        if not self.enabled:
            return
        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{stamp}] [{category}] {message}"
        with self._lock:
            self._write_raw(line)

    def _write_raw(self, line: str) -> None:
        if not self._fp:
            return
        self._fp.write(line + "\n")
        self._fp.flush()

    def close(self) -> None:
        self.set_enabled(False)
