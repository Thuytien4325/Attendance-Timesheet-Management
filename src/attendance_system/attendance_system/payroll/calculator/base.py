from __future__ import annotations

from abc import ABC, abstractmethod

from ...attendance.model import AttendanceReportRow


class PayrollCalculator(ABC):
    """Calculator interface (Strategy Pattern for payroll)."""

    @abstractmethod
    def worked_minutes(self, row: AttendanceReportRow) -> int:
        raise NotImplementedError
