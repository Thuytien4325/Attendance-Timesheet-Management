from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.attendance_system.attendance_system.attendance.model import AttendanceReportRow
from src.attendance_system.attendance_system.core.enums import AttendanceStatus
from src.attendance_system.attendance_system.payroll.service import PayrollReportService


class FakeAttendanceRepo:
    def __init__(self, rows):
        self._rows = rows
        self.last_args = None

    def get_report_rows(self, *, start_date: date, end_date: date, dept_id=None, user_id=None):
        self.last_args = {
            "start_date": start_date,
            "end_date": end_date,
            "dept_id": dept_id,
            "user_id": user_id,
        }
        return self._rows


def test_report_totals_with_break_minutes():
    rows = [
        AttendanceReportRow(
            user_id=1,
            full_name="A",
            username="a",
            dept_name="IT",
            shift_name="HC",
            break_minutes=60,
            work_date=date(2026, 1, 31),
            check_in_time=datetime(2026, 1, 31, 8, 30),
            check_out_time=datetime(2026, 1, 31, 17, 30),
            status=AttendanceStatus.ON_TIME,
        )
    ]

    svc = PayrollReportService(FakeAttendanceRepo(rows))
    report = svc.build_attendance_report(start=date(2026, 1, 31), end=date(2026, 1, 31))

    assert report.summary[0]["total_hours"] == "08:00"
    assert report.rows[0]["worked_hours"] == "08:00"


def test_report_forwards_user_id_filter():
    repo = FakeAttendanceRepo([])
    svc = PayrollReportService(repo)

    svc.build_attendance_report(start=date(2026, 1, 1), end=date(2026, 1, 31), user_id=123)

    assert repo.last_args["user_id"] == 123
