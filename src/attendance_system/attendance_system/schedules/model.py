from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Schedule:
    schedule_id: int
    user_id: int
    work_date: date
    shift_id: int
    note: Optional[str] = None
