from __future__ import annotations

import re
from itertools import islice


LINE_SPLIT_PATTERN = re.compile(r"[;,]+")


def normalize_base_url(base_url: str) -> str:
    normalized = (base_url or "").strip().rstrip("/")
    if normalized and not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized


def parse_course_references(raw_value: str) -> list[str]:
    references: list[str] = []
    seen: set[str] = set()

    for line in (raw_value or "").splitlines():
        for chunk in LINE_SPLIT_PATTERN.split(line):
            candidate = chunk.strip()
            if not candidate or candidate in seen:
                continue
            references.append(candidate)
            seen.add(candidate)

    return references


def chunked(values: list, size: int):
    iterator = iter(values)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


def mask_token(token: str) -> str:
    cleaned = (token or "").strip()
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:4]}{'*' * (len(cleaned) - 8)}{cleaned[-4:]}"


def bool_to_canvas(value: bool) -> str:
    return "true" if bool(value) else "false"
