from __future__ import annotations

from datetime import date
from typing import Optional

from ..common.validators import require_non_empty
from ..core.enums import Role
from ..core.exceptions import AuthorizationError, ValidationError
from .repository import ScheduleRepository


class ScheduleService:
    def __init__(self, schedules: ScheduleRepository):
        self._schedules = schedules

    def assign(
        self,
        *,
        current_role: Role,
        user_id: int,
        work_date: date,
        shift_id: int,
        note: Optional[str] = None,
    ) -> int:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        if int(user_id) <= 0:
            raise ValidationError("User không hợp lệ")
        if int(shift_id) <= 0:
            raise ValidationError("Ca làm việc không hợp lệ")

        note = note.strip() if note else None
        return self._schedules.upsert(user_id=int(user_id), work_date=work_date, shift_id=int(shift_id), note=note)

    def delete(self, *, current_role: Role, schedule_id: int) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        if not self._schedules.delete(schedule_id=int(schedule_id)):
            raise ValidationError("Xóa lịch thất bại")
