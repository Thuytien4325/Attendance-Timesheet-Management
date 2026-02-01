from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from ..core.enums import AttendanceStatus
from ..shifts.model import Shift
from .strategies.absent_strategy import AbsentStrategy
from .strategies.base import AttendanceStrategy
from .strategies.early_strategy import EarlyLeaveStrategy
from .strategies.late_strategy import LateStrategy
from .strategies.normal_strategy import NormalStrategy


@dataclass
class AttendanceStrategyFactory:
    """Factory Pattern: choose appropriate strategy based on rules."""

    def for_checkin(self, *, now: datetime, today: date, shift: Optional[Shift], grace_minutes: int) -> AttendanceStrategy:
        if not shift:
            return NormalStrategy()

        shift_start = datetime.combine(today, shift.start_time)
        if now <= shift_start + timedelta(minutes=grace_minutes):
            return NormalStrategy()
        return LateStrategy()

    def for_checkout(self, *, now: datetime, today: date, shift: Optional[Shift], current_status: AttendanceStatus) -> AttendanceStrategy:
        if not shift:
            return NormalStrategy()

        shift_end = datetime.combine(today, shift.end_time)
        if now < shift_end and current_status == AttendanceStatus.ON_TIME:
            return EarlyLeaveStrategy()
        return NormalStrategy()
