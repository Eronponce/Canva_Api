from __future__ import annotations

import time
from pathlib import Path


class ActivityTracker:
    def __init__(self, file_path: Path | str) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def touch(self) -> None:
        self.file_path.write_text(str(time.time_ns()), encoding="utf-8")

