from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Protocol, Sequence

from ..core.enums import AttendanceStatus
from .model import AttendanceRecord, AttendanceReportRow


class AttendanceRepository(Protocol):
    def get_recent_for_user(self, user_id: int, limit: int) -> Sequence[AttendanceRecord]:
        raise NotImplementedError

    def get_for_user_and_date(self, user_id: int, work_date: date) -> Optional[AttendanceRecord]:
        raise NotImplementedError

    def create_checkin(
        self,
        *,
        user_id: int,
        work_date: date,
        check_in_time: datetime,
        status: AttendanceStatus,
        note: Optional[str] = None,
    ) -> int:
        raise NotImplementedError

    def update_checkout(
        self,
        *,
        attendance_id: int,
        check_out_time: datetime,
        status: AttendanceStatus,
        note: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    def admin_update_record(
        self,
        *,
        attendance_id: int,
        check_in_time: datetime,
        check_out_time: Optional[datetime],
        status: AttendanceStatus,
        note: Optional[str] = None,
    ) -> bool:
        """Admin-only override used after approval workflows."""

        raise NotImplementedError

    def get_report_rows(
        self,
        *,
        start_date: date,
        end_date: date,
        dept_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Sequence[AttendanceReportRow]:
        raise NotImplementedError
