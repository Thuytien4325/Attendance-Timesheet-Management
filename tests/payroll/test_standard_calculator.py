from datetime import date, datetime

from src.attendance_system.attendance_system.core.enums import AttendanceStatus
from src.attendance_system.attendance_system.payroll.calculator.standard_calculator import StandardPayrollCalculator
from src.attendance_system.attendance_system.attendance.model import AttendanceReportRow


def test_standard_calculator_subtracts_break():
    row = AttendanceReportRow(
        user_id=1,
        full_name="A",
        username="a",
        dept_name=None,
        shift_name=None,
        break_minutes=60,
        work_date=date(2025, 1, 1),
        check_in_time=datetime(2025, 1, 1, 8, 0),
        check_out_time=datetime(2025, 1, 1, 17, 0),
        status=AttendanceStatus.ON_TIME,
        note=None,
    )

    calc = StandardPayrollCalculator()
    assert calc.worked_minutes(row) == 8 * 60
