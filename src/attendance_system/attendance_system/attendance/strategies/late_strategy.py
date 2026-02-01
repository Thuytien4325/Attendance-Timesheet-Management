from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from ...core.enums import AttendanceStatus
from ...shifts.model import Shift
from .base import AttendanceStrategy, StatusDecision


class LateStrategy(AttendanceStrategy):
    """Late check-in."""

    def decide_checkin(self, *, now: datetime, today: date, shift: Optional[Shift], grace_minutes: int) -> StatusDecision:
        return StatusDecision(status=AttendanceStatus.LATE)

    def decide_checkout(self, *, now: datetime, today: date, shift: Optional[Shift], current: AttendanceStatus) -> StatusDecision:
        return StatusDecision(status=current)
