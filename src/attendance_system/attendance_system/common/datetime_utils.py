from __future__ import annotations

from datetime import date, datetime


def parse_iso_date(value: str) -> date:
    """Parse YYYY-MM-DD string into date."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def now_local() -> datetime:
    """Current local time.

    Note: Wrapped so tests can patch/mocked easier.
    """
    return datetime.now()
