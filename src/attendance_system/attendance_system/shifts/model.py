from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class Shift:
    """Thực thể miền (domain): Ca làm việc (Shift)."""

    shift_id: int
    shift_name: str
    start_time: time
    end_time: time
    break_minutes: int = 0
