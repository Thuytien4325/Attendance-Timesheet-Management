from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from ..common.validators import require_min_length, require_non_empty
from ..core.enums import Role
from ..core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from datetime import date

from ..schedules.repository import ScheduleRepository
from ..shifts.repository import ShiftRepository
from .repository import UserRepository


@dataclass(frozen=True)
class SessionUser:
    """What we store into Flask session after login."""

    user_id: int
    full_name: str
    role: Role
    dept_id: Optional[int]
    shift_id: Optional[int]
    shift_info: str


class AuthService:
    """Use case: authenticate user (login)."""

    def __init__(self, users: UserRepository, shifts: ShiftRepository, schedules: Optional[ScheduleRepository] = None):
        self._users = users
        self._shifts = shifts
        self._schedules = schedules

    def get_shift_info_for_date(self, *, user_id: int, fallback_shift_id: Optional[int], work_date: date) -> str:
        shift = None
        if self._schedules:
            sc = self._schedules.get_for_user_and_date(user_id=user_id, work_date=work_date)
            if sc:
                shift = self._shifts.get_by_id(sc.shift_id)

        if not shift and fallback_shift_id:
            shift = self._shifts.get_by_id(fallback_shift_id)

        if not shift:
            return "Chưa xếp ca"
        def _fmt(t) -> str:
            # Accept datetime.time (expected), but also tolerate timedelta/str from drivers.
            try:
                return t.strftime("%H:%M")
            except Exception:
                return str(t)[:5]

        return f"{shift.shift_name} ({_fmt(shift.start_time)} - {_fmt(shift.end_time)})"

    def authenticate(self, username: str, password: str) -> SessionUser:
        user = self._users.get_by_username(username)
        if not user or not user.is_active:
            raise AuthenticationError("Sai tài khoản hoặc mật khẩu")

        try:
            ok = check_password_hash(user.password_hash, password)
        except Exception:
            # e.g. placeholder hashes like 'CHANGE_ME' or corrupted values
            ok = False

        if not ok:
            raise AuthenticationError("Sai tài khoản hoặc mật khẩu")

        shift_info = self.get_shift_info_for_date(user_id=user.user_id, fallback_shift_id=user.shift_id, work_date=date.today())

        return SessionUser(
            user_id=user.user_id,
            full_name=user.full_name,
            role=user.role,
            dept_id=user.dept_id,
            shift_id=user.shift_id,
            shift_info=shift_info,
        )


class UserService:
    """Use case: manage users (admin)."""

    def __init__(self, users: UserRepository):
        self._users = users

    def create_account(
        self,
        *,
        full_name: str,
        username: str,
        password: str,
        role: Role,
        dept_id: int,
        shift_id: int,
    ) -> int:
        full_name = require_non_empty(full_name, "Họ tên")
        username = require_non_empty(username, "Tên đăng nhập")
        require_min_length(password, "Mật khẩu", 6)

        if self._users.get_by_username(username):
            raise ValidationError("Tên đăng nhập đã tồn tại")

        if role == Role.ADMIN:
            raise ValidationError("Không tạo Admin từ màn hình này")

        password_hash = generate_password_hash(password)
        return self._users.create_user(
            full_name=full_name,
            username=username,
            password_hash=password_hash,
            role=role,
            dept_id=int(dept_id),
            shift_id=int(shift_id),
        )

    def create_user(self, *, full_name: str, username: str, password: str, dept_id: int, shift_id: int) -> int:
        return self.create_account(
            full_name=full_name,
            username=username,
            password=password,
            role=Role.USER,
            dept_id=dept_id,
            shift_id=shift_id,
        )

    def create_staff(self, *, full_name: str, username: str, password: str, dept_id: int, shift_id: int) -> int:
        return self.create_account(
            full_name=full_name,
            username=username,
            password=password,
            role=Role.STAFF,
            dept_id=dept_id,
            shift_id=shift_id,
        )

    def list_admin_view(self):
        return self._users.list_admin_view()

    def delete_user(self, *, current_role: Role, user_id: int) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        user = self._users.get_by_id(user_id)
        if not user:
            raise ValidationError("Nhân viên không tồn tại")
        if user.role == Role.ADMIN:
            raise ValidationError("Không thể xóa tài khoản Admin")

        if not self._users.delete_by_id(user_id):
            raise ValidationError("Xóa nhân viên thất bại")
