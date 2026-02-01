from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

from ..attendance.repository import AttendanceRepository
from ..common.validators import require_non_empty
from ..core.enums import AttendanceStatus, RequestStatus, Role
from ..core.exceptions import AuthorizationError, ValidationError
from ..schedules.repository import ScheduleRepository
from .repository import RequestRepository


@dataclass(frozen=True)
class NewTimesheetAdjustment:
    work_date: date
    requested_check_in: Optional[time]
    requested_check_out: Optional[time]
    requested_note: Optional[str]


class RequestService:
    def __init__(self, requests: RequestRepository, attendance: AttendanceRepository, schedules: ScheduleRepository):
        self._requests = requests
        self._attendance = attendance
        self._schedules = schedules

    @staticmethod
    def _parse_time(value: str) -> Optional[time]:
        v = (value or "").strip()
        if not v:
            return None
        try:
            return datetime.strptime(v, "%H:%M").time()
        except ValueError:
            raise ValidationError("Giờ không hợp lệ (HH:MM)")

    def create_timesheet_adjustment(
        self,
        *,
        current_role: Role,
        user_id: int,
        work_date: date,
        requested_check_in: str,
        requested_check_out: str,
        requested_note: str,
    ) -> int:
        if current_role != Role.STAFF:
            raise AuthorizationError("Chỉ Staff mới được gửi yêu cầu chỉnh sửa")

        rec = self._attendance.get_for_user_and_date(int(user_id), work_date)
        if not rec:
            raise ValidationError("Không tìm thấy bản ghi chấm công của ngày này")

        check_in_t = self._parse_time(requested_check_in)
        check_out_t = self._parse_time(requested_check_out)
        note = (requested_note or "").strip() or None

        if not check_in_t and not check_out_t and not note:
            raise ValidationError("Vui lòng nhập ít nhất 1 thay đổi")

        return self._requests.create_timesheet_adjustment(
            user_id=int(user_id),
            work_date=work_date,
            requested_check_in=check_in_t,
            requested_check_out=check_out_t,
            requested_note=note,
        )

    def approve_timesheet_adjustment(
        self,
        *,
        current_role: Role,
        admin_user_id: int,
        request_id: int,
        admin_note: str = "",
    ) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        req = self._requests.get_timesheet_adjustment(request_id=int(request_id))
        if not req:
            raise ValidationError("Yêu cầu không tồn tại")
        if req.status != RequestStatus.PENDING:
            raise ValidationError("Yêu cầu đã được xử lý")

        rec = self._attendance.get_for_user_and_date(req.user_id, req.work_date)
        if not rec:
            raise ValidationError("Không tìm thấy bản ghi chấm công để áp dụng")

        new_check_in = rec.check_in_time
        new_check_out = rec.check_out_time
        if req.requested_check_in:
            new_check_in = datetime.combine(req.work_date, req.requested_check_in)
        if req.requested_check_out:
            new_check_out = datetime.combine(req.work_date, req.requested_check_out)

        new_note = req.requested_note if req.requested_note is not None else rec.note

        status = rec.status
        if new_check_out and new_check_in and new_check_out < new_check_in:
            raise ValidationError("Giờ ra không thể nhỏ hơn giờ vào")

        ok = self._attendance.admin_update_record(
            attendance_id=rec.attendance_id,
            check_in_time=new_check_in,
            check_out_time=new_check_out,
            status=status,
            note=new_note,
        )
        if not ok:
            raise ValidationError("Cập nhật chấm công thất bại")

        decided = self._requests.decide_timesheet_adjustment(
            request_id=int(request_id),
            status=RequestStatus.APPROVED,
            decided_by=int(admin_user_id),
            admin_note=(admin_note or "").strip() or None,
        )
        if not decided:
            raise ValidationError("Duyệt yêu cầu thất bại")

    def reject_timesheet_adjustment(
        self,
        *,
        current_role: Role,
        admin_user_id: int,
        request_id: int,
        admin_note: str = "",
    ) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        decided = self._requests.decide_timesheet_adjustment(
            request_id=int(request_id),
            status=RequestStatus.REJECTED,
            decided_by=int(admin_user_id),
            admin_note=(admin_note or "").strip() or None,
        )
        if not decided:
            raise ValidationError("Từ chối yêu cầu thất bại")

    def create_leave(
        self,
        *,
        current_role: Role,
        user_id: int,
        start_date: date,
        end_date: date,
        reason: str,
    ) -> int:
        if current_role not in {Role.USER, Role.STAFF}:
            raise AuthorizationError("Bạn không có quyền")

        if end_date < start_date:
            raise ValidationError("Ngày kết thúc phải >= ngày bắt đầu")

        reason = require_non_empty(reason, "Lý do")
        return self._requests.create_leave(
            user_id=int(user_id),
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )

    def approve_leave(
        self,
        *,
        current_role: Role,
        admin_user_id: int,
        request_id: int,
        admin_note: str = "",
    ) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        ok = self._requests.decide_leave(
            request_id=int(request_id),
            status=RequestStatus.APPROVED,
            decided_by=int(admin_user_id),
            admin_note=(admin_note or "").strip() or None,
        )
        if not ok:
            raise ValidationError("Duyệt yêu cầu thất bại")

    def reject_leave(
        self,
        *,
        current_role: Role,
        admin_user_id: int,
        request_id: int,
        admin_note: str = "",
    ) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        ok = self._requests.decide_leave(
            request_id=int(request_id),
            status=RequestStatus.REJECTED,
            decided_by=int(admin_user_id),
            admin_note=(admin_note or "").strip() or None,
        )
        if not ok:
            raise ValidationError("Từ chối yêu cầu thất bại")

    def create_schedule_change(
        self,
        *,
        current_role: Role,
        user_id: int,
        work_date: date,
        requested_shift_id: int,
        requested_note: str,
    ) -> int:
        if current_role != Role.STAFF:
            raise AuthorizationError("Chỉ Staff mới được gửi đề xuất lịch làm")

        if int(requested_shift_id) <= 0:
            raise ValidationError("Ca làm việc không hợp lệ")

        note = require_non_empty(requested_note, "Ghi chú")
        return self._requests.create_schedule_change(
            user_id=int(user_id),
            work_date=work_date,
            requested_shift_id=int(requested_shift_id),
            requested_note=note,
        )

    def approve_schedule_change(
        self,
        *,
        current_role: Role,
        admin_user_id: int,
        request_id: int,
        admin_note: str = "",
    ) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        req = self._requests.get_schedule_change(request_id=int(request_id))
        if not req:
            raise ValidationError("Yêu cầu không tồn tại")
        if req.status != RequestStatus.PENDING:
            raise ValidationError("Yêu cầu đã được xử lý")

        schedule_id = self._schedules.upsert(
            user_id=int(req.user_id),
            work_date=req.work_date,
            shift_id=int(req.requested_shift_id),
            note=req.requested_note,
        )
        if schedule_id <= 0:
            raise ValidationError("Áp dụng lịch làm thất bại")

        decided = self._requests.decide_schedule_change(
            request_id=int(request_id),
            status=RequestStatus.APPROVED,
            decided_by=int(admin_user_id),
            admin_note=(admin_note or "").strip() or None,
        )
        if not decided:
            raise ValidationError("Duyệt yêu cầu thất bại")

    def reject_schedule_change(
        self,
        *,
        current_role: Role,
        admin_user_id: int,
        request_id: int,
        admin_note: str = "",
    ) -> None:
        if current_role != Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền")

        decided = self._requests.decide_schedule_change(
            request_id=int(request_id),
            status=RequestStatus.REJECTED,
            decided_by=int(admin_user_id),
            admin_note=(admin_note or "").strip() or None,
        )
        if not decided:
            raise ValidationError("Từ chối yêu cầu thất bại")

    def list_my_requests(self, *, user_id: int) -> dict:
        return {
            "adjustments": self._requests.list_timesheet_adjustments(user_id=int(user_id), limit=200),
            "leaves": self._requests.list_leave_requests(user_id=int(user_id), limit=200),
            "schedule_changes": self._requests.list_schedule_change_requests(user_id=int(user_id), limit=200),
        }

    def list_admin_pending(self) -> dict:
        return {
            "adjustments": self._requests.list_timesheet_adjustments(status=RequestStatus.PENDING, limit=500),
            "leaves": self._requests.list_leave_requests(status=RequestStatus.PENDING, limit=500),
            "schedule_changes": self._requests.list_schedule_change_requests(status=RequestStatus.PENDING, limit=500),
        }
