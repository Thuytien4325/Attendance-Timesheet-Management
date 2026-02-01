from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from ..core.enums import AttendanceStatus


@dataclass(frozen=True)
class AttendanceRecord:
    """Thực thể miền (domain): Bản ghi chấm công."""

    attendance_id: int
    user_id: int
    work_date: date
    check_in_time: datetime
    check_out_time: Optional[datetime]
    status: AttendanceStatus
    note: Optional[str] = None


@dataclass(frozen=True)
class AttendanceReportRow:
    """Read-model phục vụ báo cáo/xuất file (tối ưu cho truy vấn)."""

    user_id: int
    full_name: str
    username: str
    dept_name: Optional[str]
    shift_name: Optional[str]
    break_minutes: int
    work_date: date
    check_in_time: datetime
    check_out_time: Optional[datetime]
    status: AttendanceStatus
    note: Optional[str] = None
