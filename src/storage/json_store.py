from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Callable


class JsonFileStore:
    def __init__(self, path: Path, default_factory: Callable[[], object]):
        self.path = path
        self.default_factory = default_factory
        self._lock = RLock()
        self.ensure_exists()

    def ensure_exists(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_unlocked(self.default_factory())

    def _read_unlocked(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8") or "null")
        except json.JSONDecodeError:
            default_value = self.default_factory()
            self._write_unlocked(default_value)
            return default_value

    def read(self):
        with self._lock:
            return self._read_unlocked()

    def _write_unlocked(self, data) -> None:
        temp_file = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_file.replace(self.path)

    def write(self, data) -> None:
        with self._lock:
            self._write_unlocked(data)

    def update(self, updater):
        with self._lock:
            current = self._read_unlocked()
            updated = updater(current)
            self._write_unlocked(updated)
            return updated
