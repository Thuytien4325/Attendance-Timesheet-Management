from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..core.enums import AttendanceStatus
from ..core.exceptions import ValidationError
from ..schedules.repository import ScheduleRepository
from ..shifts.repository import ShiftRepository
from ..users.repository import UserRepository
from .factory import AttendanceStrategyFactory
from .repository import AttendanceRepository


@dataclass(frozen=True)
class AttendanceRowUI:
    date: str
    check_in: str
    check_out: str
    status: str
    css_class: str


class AttendanceService:
    def __init__(
        self,
        attendance: AttendanceRepository,
        users: UserRepository,
        shifts: ShiftRepository,
        schedules: ScheduleRepository | None = None,
        *,
        strategy_factory: AttendanceStrategyFactory | None = None,
        grace_minutes: int = 5,
    ):
        self._attendance = attendance
        self._users = users
        self._shifts = shifts
        self._schedules = schedules
        self._factory = strategy_factory or AttendanceStrategyFactory()
        self._grace_minutes = int(grace_minutes)

    def _get_effective_shift(self, *, user_id: int, work_date: date, fallback_shift_id: int | None):
        if self._schedules:
            sc = self._schedules.get_for_user_and_date(user_id=user_id, work_date=work_date)
            if sc:
                return self._shifts.get_by_id(sc.shift_id)

        if fallback_shift_id:
            return self._shifts.get_by_id(fallback_shift_id)
        return None

    def check_in(self, user_id: int, *, now: datetime | None = None) -> None:
        now = now or datetime.now()
        today = now.date()

        user = self._users.get_by_id(user_id)
        if not user:
            raise ValidationError("Nhân viên không tồn tại")

        existing = self._attendance.get_for_user_and_date(user_id, today)
        if existing:
            raise ValidationError("Bạn đã chấm công vào ca hôm nay rồi")

        shift = self._get_effective_shift(user_id=user_id, work_date=today, fallback_shift_id=user.shift_id)
        strategy = self._factory.for_checkin(now=now, today=today, shift=shift, grace_minutes=self._grace_minutes)
        decision = strategy.decide_checkin(now=now, today=today, shift=shift, grace_minutes=self._grace_minutes)

        self._attendance.create_checkin(
            user_id=user_id,
            work_date=today,
            check_in_time=now,
            status=decision.status,
            note=decision.note,
        )

    def check_out(self, user_id: int, *, now: datetime | None = None) -> None:
        now = now or datetime.now()
        today = now.date()

        record = self._attendance.get_for_user_and_date(user_id, today)
        if not record:
            raise ValidationError("Bạn chưa chấm công vào ca hôm nay")
        if record.check_out_time is not None:
            raise ValidationError("Bạn đã chấm công tan ca rồi")

        user = self._users.get_by_id(user_id)
        if not user:
            raise ValidationError("Nhân viên không tồn tại")

        shift = self._get_effective_shift(user_id=user_id, work_date=today, fallback_shift_id=user.shift_id)
        strategy = self._factory.for_checkout(now=now, today=today, shift=shift, current_status=record.status)
        decision = strategy.decide_checkout(now=now, today=today, shift=shift, current=record.status)

        self._attendance.update_checkout(
            attendance_id=record.attendance_id,
            check_out_time=now,
            status=decision.status,
            note=decision.note or record.note,
        )

    def get_history_ui(self, user_id: int, *, limit: int = 15):
        rows = self._attendance.get_recent_for_user(user_id, limit)
        return [self._to_ui(r) for r in rows]

    def get_today_record(self, user_id: int, today: date):
        """Get today's attendance record for a user"""
        return self._attendance.get_for_user_and_date(user_id, today)

    def _to_ui(self, r) -> dict:
        status = r.status
        label = {
            AttendanceStatus.ON_TIME: "Đúng giờ",
            AttendanceStatus.LATE: "Đi muộn",
            AttendanceStatus.EARLY_LEAVE: "Về sớm",
            AttendanceStatus.ABSENT: "Vắng",
            AttendanceStatus.UNKNOWN: "Không xác định",
        }.get(status, status.value)

        css = {
            AttendanceStatus.ON_TIME: "bg-success",
            AttendanceStatus.LATE: "bg-danger",
            AttendanceStatus.EARLY_LEAVE: "bg-warning text-dark",
            AttendanceStatus.ABSENT: "bg-secondary",
            AttendanceStatus.UNKNOWN: "bg-secondary",
        }.get(status, "bg-secondary")

        return {
            "date": r.work_date.strftime("%Y-%m-%d"),
            "check_in": r.check_in_time.strftime("%H:%M:%S"),
            "check_out": r.check_out_time.strftime("%H:%M:%S") if r.check_out_time else "-",
            "status": label,
            "css_class": css,
        }
