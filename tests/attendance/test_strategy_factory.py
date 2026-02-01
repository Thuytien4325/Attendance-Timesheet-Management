from datetime import date, datetime, time

from src.attendance_system.attendance_system.attendance.factory import AttendanceStrategyFactory
from src.attendance_system.attendance_system.attendance.strategies.late_strategy import LateStrategy
from src.attendance_system.attendance_system.attendance.strategies.normal_strategy import NormalStrategy
from src.attendance_system.attendance_system.shifts.model import Shift


def test_factory_checkin_on_time_within_grace():
    shift = Shift(shift_id=1, shift_name="Morning", start_time=time(8, 0), end_time=time(17, 0), break_minutes=60)
    today = date(2025, 1, 1)
    now = datetime(2025, 1, 1, 8, 4, 59)

    factory = AttendanceStrategyFactory()
    strategy = factory.for_checkin(now=now, today=today, shift=shift, grace_minutes=5)

    assert isinstance(strategy, NormalStrategy)


def test_factory_checkin_late_after_grace():
    shift = Shift(shift_id=1, shift_name="Morning", start_time=time(8, 0), end_time=time(17, 0), break_minutes=60)
    today = date(2025, 1, 1)
    now = datetime(2025, 1, 1, 8, 6, 0)

    factory = AttendanceStrategyFactory()
    strategy = factory.for_checkin(now=now, today=today, shift=shift, grace_minutes=5)

    assert isinstance(strategy, LateStrategy)
