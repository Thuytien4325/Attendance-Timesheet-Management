from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

from ..core.enums import RequestStatus


@dataclass(frozen=True)
class TimesheetAdjustmentRequest:
    request_id: int
    user_id: int
    work_date: date
    requested_check_in: Optional[time]
    requested_check_out: Optional[time]
    requested_note: Optional[str]
    status: RequestStatus
    created_at: datetime
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    admin_note: Optional[str] = None


@dataclass(frozen=True)
class LeaveRequest:
    request_id: int
    user_id: int
    start_date: date
    end_date: date
    reason: str
    status: RequestStatus
    created_at: datetime
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    admin_note: Optional[str] = None


@dataclass(frozen=True)
class ScheduleChangeRequest:
    request_id: int
    user_id: int
    work_date: date
    requested_shift_id: int
    requested_note: str
    status: RequestStatus
    created_at: datetime
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    admin_note: Optional[str] = None
