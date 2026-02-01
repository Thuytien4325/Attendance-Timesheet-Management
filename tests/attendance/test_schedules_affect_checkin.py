from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

from werkzeug.security import generate_password_hash

from src.attendance_system.attendance_system.attendance.model import AttendanceRecord
from src.attendance_system.attendance_system.attendance.service import AttendanceService
from src.attendance_system.attendance_system.core.enums import AttendanceStatus, Role
from src.attendance_system.attendance_system.shifts.model import Shift
from src.attendance_system.attendance_system.users.model import User


@dataclass
class InMemoryUsers:
    users_by_id: dict[int, User]

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.users_by_id.get(user_id)


@dataclass
class InMemoryShifts:
    shifts: dict[int, Shift]

    def get_by_id(self, shift_id: int) -> Optional[Shift]:
        return self.shifts.get(shift_id)


@dataclass
class InMemorySchedules:
    shift_by_user_date: dict[tuple[int, date], int]

    def get_for_user_and_date(self, *, user_id: int, work_date: date):
        shift_id = self.shift_by_user_date.get((user_id, work_date))
        if not shift_id:
            return None

        class _Sc:
            def __init__(self, shift_id: int):
                self.shift_id = shift_id

        return _Sc(shift_id)


class InMemoryAttendance:
    def __init__(self):
        self._by_user_date: dict[tuple[int, date], AttendanceRecord] = {}
        self._id = 0

    def get_for_user_and_date(self, user_id: int, work_date: date) -> Optional[AttendanceRecord]:
        return self._by_user_date.get((user_id, work_date))

    def get_recent_for_user(self, user_id: int, limit: int):
        items = [r for r in self._by_user_date.values() if r.user_id == user_id]
        items.sort(key=lambda r: r.check_in_time, reverse=True)
        return items[:limit]

    def create_checkin(self, *, user_id: int, work_date: date, check_in_time: datetime, status: AttendanceStatus, note=None) -> int:
        self._id += 1
        rec = AttendanceRecord(
            attendance_id=self._id,
            user_id=user_id,
            work_date=work_date,
            check_in_time=check_in_time,
            check_out_time=None,
            status=status,
            note=note,
        )
        self._by_user_date[(user_id, work_date)] = rec
        return self._id

    def update_checkout(self, *, attendance_id: int, check_out_time: datetime, status: AttendanceStatus, note=None) -> bool:
        return False


def test_scheduled_shift_makes_checkin_late():
    # User default shift starts at 10:00 (would be ON_TIME at 08:06)
    # But schedule assigns shift starting at 08:00 => 08:06 is LATE (grace 5)
    shift_default = Shift(shift_id=1, shift_name="Default", start_time=time(10, 0), end_time=time(18, 0))
    shift_scheduled = Shift(shift_id=2, shift_name="Scheduled", start_time=time(8, 0), end_time=time(17, 0))

    user = User(
        user_id=1,
        full_name="A",
        username="a",
        password_hash=generate_password_hash("pw"),
        role=Role.STAFF,
        dept_id=1,
        shift_id=1,
        is_active=True,
    )

    now = datetime(2026, 2, 1, 8, 6, 0)

    attendance_repo = InMemoryAttendance()
    users_repo = InMemoryUsers({1: user})
    shifts_repo = InMemoryShifts({1: shift_default, 2: shift_scheduled})
    schedules_repo = InMemorySchedules({(1, now.date()): 2})

    svc = AttendanceService(attendance_repo, users_repo, shifts_repo, schedules_repo, grace_minutes=5)
    svc.check_in(1, now=now)

    rec = attendance_repo.get_for_user_and_date(1, now.date())
    assert rec is not None
    assert rec.status == AttendanceStatus.LATE
