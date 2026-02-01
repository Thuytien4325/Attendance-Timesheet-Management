from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

import pytest

from src.attendance_system.attendance_system.attendance.model import AttendanceRecord
from src.attendance_system.attendance_system.attendance.service import AttendanceService
from src.attendance_system.attendance_system.core.enums import AttendanceStatus, Role
from src.attendance_system.attendance_system.core.exceptions import AuthenticationError
from src.attendance_system.attendance_system.shifts.model import Shift
from src.attendance_system.attendance_system.users.model import User
from src.attendance_system.attendance_system.users.service import AuthService


@dataclass
class InMemoryUsers:
    users_by_username: dict[str, User]
    users_by_id: dict[int, User]

    def get_by_username(self, username: str) -> Optional[User]:
        return self.users_by_username.get(username)

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.users_by_id.get(user_id)


@dataclass
class InMemoryShifts:
    shifts: dict[int, Shift]

    def get_by_id(self, shift_id: int) -> Optional[Shift]:
        return self.shifts.get(shift_id)


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
        for k, v in list(self._by_user_date.items()):
            if v.attendance_id == attendance_id:
                self._by_user_date[k] = AttendanceRecord(
                    attendance_id=v.attendance_id,
                    user_id=v.user_id,
                    work_date=v.work_date,
                    check_in_time=v.check_in_time,
                    check_out_time=check_out_time,
                    status=status,
                    note=note,
                )
                return True
        return False


def test_auth_wrong_password_raises():
    from werkzeug.security import generate_password_hash

    user = User(
        user_id=1,
        full_name="A",
        username="a",
        password_hash=generate_password_hash("right"),
        role=Role.STAFF,
        dept_id=None,
        shift_id=None,
        is_active=True,
    )

    auth = AuthService(InMemoryUsers({"a": user}, {1: user}), InMemoryShifts({}))

    with pytest.raises(AuthenticationError):
        auth.authenticate("a", "wrong")


def test_attendance_checkin_on_time(fixed_now):
    from werkzeug.security import generate_password_hash

    shift = Shift(shift_id=1, shift_name="Hành chính", start_time=time(8, 30), end_time=time(17, 30))
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

    attendance_repo = InMemoryAttendance()
    svc = AttendanceService(attendance_repo, InMemoryUsers({"a": user}, {1: user}), InMemoryShifts({1: shift}), grace_minutes=5)

    svc.check_in(1, now=fixed_now)
    rec = attendance_repo.get_for_user_and_date(1, fixed_now.date())
    assert rec is not None
    assert rec.status == AttendanceStatus.ON_TIME
