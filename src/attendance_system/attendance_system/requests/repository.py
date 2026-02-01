from __future__ import annotations

from datetime import date, time
from typing import Optional, Protocol, Sequence

from ..core.enums import RequestStatus
from .model import LeaveRequest, ScheduleChangeRequest, TimesheetAdjustmentRequest


class RequestRepository(Protocol):
    # Timesheet adjustments
    def create_timesheet_adjustment(
        self,
        *,
        user_id: int,
        work_date: date,
        requested_check_in: Optional[time],
        requested_check_out: Optional[time],
        requested_note: Optional[str],
    ) -> int:
        raise NotImplementedError

    def get_timesheet_adjustment(self, *, request_id: int) -> Optional[TimesheetAdjustmentRequest]:
        raise NotImplementedError

    def list_timesheet_adjustments(
        self,
        *,
        status: Optional[RequestStatus] = None,
        user_id: Optional[int] = None,
        limit: int = 200,
    ) -> Sequence[dict]:
        """Return UI rows (joined with user)."""

        raise NotImplementedError

    def decide_timesheet_adjustment(
        self,
        *,
        request_id: int,
        status: RequestStatus,
        decided_by: int,
        admin_note: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    # Leave requests
    def create_leave(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        reason: str,
    ) -> int:
        raise NotImplementedError

    def list_leave_requests(
        self,
        *,
        status: Optional[RequestStatus] = None,
        user_id: Optional[int] = None,
        limit: int = 200,
    ) -> Sequence[dict]:
        raise NotImplementedError

    def decide_leave(
        self,
        *,
        request_id: int,
        status: RequestStatus,
        decided_by: int,
        admin_note: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    # Schedule change requests
    def create_schedule_change(
        self,
        *,
        user_id: int,
        work_date: date,
        requested_shift_id: int,
        requested_note: str,
    ) -> int:
        raise NotImplementedError

    def get_schedule_change(self, *, request_id: int) -> Optional[ScheduleChangeRequest]:
        raise NotImplementedError

    def list_schedule_change_requests(
        self,
        *,
        status: Optional[RequestStatus] = None,
        user_id: Optional[int] = None,
        limit: int = 200,
    ) -> Sequence[dict]:
        """Trả về dữ liệu phục vụ UI (join với user/shift)."""

        raise NotImplementedError

    def decide_schedule_change(
        self,
        *,
        request_id: int,
        status: RequestStatus,
        decided_by: int,
        admin_note: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError
