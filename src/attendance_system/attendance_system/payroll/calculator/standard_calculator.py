from __future__ import annotations

from .base import PayrollCalculator
from ...attendance.model import AttendanceReportRow


class StandardPayrollCalculator(PayrollCalculator):
    """Standard rule: (out - in) - break_minutes, not below 0."""

    def worked_minutes(self, row: AttendanceReportRow) -> int:
        if not row.check_out_time:
            return 0
        minutes = int((row.check_out_time - row.check_in_time).total_seconds() // 60)
        minutes -= int(row.break_minutes or 0)
        return max(minutes, 0)
