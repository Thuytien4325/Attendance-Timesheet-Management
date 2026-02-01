from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from ...core.enums import AttendanceStatus
from ...shifts.model import Shift


@dataclass(frozen=True)
class StatusDecision:
    status: AttendanceStatus
    note: Optional[str] = None


class AttendanceStrategy(ABC):
    """Strategy Pattern: encapsulate how we decide an attendance status."""

    @abstractmethod
    def decide_checkin(self, *, now: datetime, today: date, shift: Optional[Shift], grace_minutes: int) -> StatusDecision:
        raise NotImplementedError

    @abstractmethod
    def decide_checkout(self, *, now: datetime, today: date, shift: Optional[Shift], current: AttendanceStatus) -> StatusDecision:
        raise NotImplementedError
