from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..attendance.repository import AttendanceRepository
from .calculator.base import PayrollCalculator
from .calculator.standard_calculator import StandardPayrollCalculator


@dataclass(frozen=True)
class ReportData:
    rows: list[dict]
    summary: list[dict]


class PayrollReportService:
    def __init__(
        self,
        attendance: AttendanceRepository,
        *,
        calculator: Optional[PayrollCalculator] = None,
    ):
        self._attendance = attendance
        self._calculator = calculator or StandardPayrollCalculator()

    def build_attendance_report(
        self,
        *,
        start: date,
        end: date,
        user_id: Optional[int] = None,
        dept_id: Optional[int] = None,
    ) -> ReportData:
        query_rows = self._attendance.get_report_rows(start_date=start, end_date=end, user_id=user_id, dept_id=dept_id)

        summary_map: dict[int, dict] = {}
        out_rows: list[dict] = []

        for r in query_rows:
            minutes = self._calculator.worked_minutes(r)
            worked_hours = f"{minutes // 60:02d}:{minutes % 60:02d}"

            out_rows.append(
                {
                    "user_id": r.user_id,
                    "full_name": r.full_name,
                    "username": r.username,
                    "dept_name": r.dept_name or "-",
                    "shift_name": r.shift_name or "-",
                    "work_date": r.work_date.strftime("%Y-%m-%d"),
                    "check_in": r.check_in_time.strftime("%H:%M"),
                    "check_out": r.check_out_time.strftime("%H:%M") if r.check_out_time else "-",
                    "worked_hours": worked_hours,
                    "status": r.status.value,
                    "note": r.note or "",
                }
            )

            s = summary_map.get(r.user_id)
            if not s:
                s = {
                    "user_id": r.user_id,
                    "full_name": r.full_name,
                    "username": r.username,
                    "total_minutes": 0,
                }
                summary_map[r.user_id] = s
            s["total_minutes"] += minutes

        summary = []
        for s in summary_map.values():
            total_minutes = int(s["total_minutes"])
            total_hours = f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"
            summary.append(
                {
                    "user_id": s["user_id"],
                    "full_name": s["full_name"],
                    "username": s["username"],
                    "total_hours": total_hours,
                }
            )

        summary.sort(key=lambda x: x["total_hours"], reverse=True)
        return ReportData(rows=out_rows, summary=summary)
