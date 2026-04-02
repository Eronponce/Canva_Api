from __future__ import annotations

from src.storage.json_store import JsonFileStore


class HistoryStore:
    def __init__(self, history_file, limit: int = 25):
        self.store = JsonFileStore(history_file, list)
        self.limit = limit

    def list_entries(self) -> list[dict]:
        entries = self.store.read() or []
        return sorted(entries, key=lambda item: item.get("created_at", ""), reverse=True)

    def get_entry(self, job_id: str) -> dict | None:
        for entry in self.list_entries():
            if entry.get("id") == job_id:
                return entry
        return None

    def append_entry(self, entry: dict) -> None:
        def updater(entries):
            filtered = [item for item in entries if item.get("id") != entry.get("id")]
            filtered.insert(0, entry)
            return filtered[: self.limit]

        self.store.update(updater)
