from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def datetime_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_schedule_datetime(schedule_local: str, client_timezone: str | None) -> str | None:
    if not schedule_local:
        return None

    normalized = schedule_local.strip().replace("Z", "+00:00")
    schedule_dt = datetime.fromisoformat(normalized)
    if schedule_dt.tzinfo is None:
        timezone = ZoneInfo(client_timezone or "UTC")
        schedule_dt = schedule_dt.replace(tzinfo=timezone)
    return schedule_dt.replace(microsecond=0).isoformat()


def iso_to_display(value: str | None) -> str:
    if not value:
        return "-"
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
