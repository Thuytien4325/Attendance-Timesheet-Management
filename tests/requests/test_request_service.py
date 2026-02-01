from __future__ import annotations

from datetime import date, datetime, time

import pytest

from src.attendance_system.attendance_system.core.enums import AttendanceStatus, RequestStatus, Role
from src.attendance_system.attendance_system.core.exceptions import AuthorizationError, ValidationError
from src.attendance_system.attendance_system.requests.model import ScheduleChangeRequest, TimesheetAdjustmentRequest
from src.attendance_system.attendance_system.requests.service import RequestService


class FakeRequestsRepo:
    def __init__(self):
        self._next_id = 1
        self._adj: dict[int, TimesheetAdjustmentRequest] = {}
        self._sch: dict[int, ScheduleChangeRequest] = {}

    def create_timesheet_adjustment(self, *, user_id, work_date, requested_check_in, requested_check_out, requested_note):
        rid = self._next_id
        self._next_id += 1
        self._adj[rid] = TimesheetAdjustmentRequest(
            request_id=rid,
            user_id=user_id,
            work_date=work_date,
            requested_check_in=requested_check_in,
            requested_check_out=requested_check_out,
            requested_note=requested_note,
            status=RequestStatus.PENDING,
            created_at=datetime(2026, 2, 1, 10, 0, 0),
        )
        return rid

    def get_timesheet_adjustment(self, *, request_id):
        return self._adj.get(int(request_id))

    def decide_timesheet_adjustment(self, *, request_id, status, decided_by, admin_note=None):
        req = self._adj.get(int(request_id))
        if not req or req.status != RequestStatus.PENDING:
            return False
        self._adj[int(request_id)] = TimesheetAdjustmentRequest(
            request_id=req.request_id,
            user_id=req.user_id,
            work_date=req.work_date,
            requested_check_in=req.requested_check_in,
            requested_check_out=req.requested_check_out,
            requested_note=req.requested_note,
            status=status,
            created_at=req.created_at,
            decided_by=decided_by,
            decided_at=datetime(2026, 2, 1, 11, 0, 0),
            admin_note=admin_note,
        )
        return True

    # leave methods used by service list calls
    def create_leave(self, *, user_id, start_date, end_date, reason):
        return 1

    def list_timesheet_adjustments(self, *, status=None, user_id=None, limit=200):
        return []

    def list_leave_requests(self, *, status=None, user_id=None, limit=200):
        return []

    def decide_leave(self, *, request_id, status, decided_by, admin_note=None):
        return True

    # schedule change methods
    def create_schedule_change(self, *, user_id, work_date, requested_shift_id, requested_note):
        rid = self._next_id
        self._next_id += 1
        self._sch[rid] = ScheduleChangeRequest(
            request_id=rid,
            user_id=int(user_id),
            work_date=work_date,
            requested_shift_id=int(requested_shift_id),
            requested_note=requested_note,
            status=RequestStatus.PENDING,
            created_at=datetime(2026, 2, 1, 10, 0, 0),
        )
        return rid

    def get_schedule_change(self, *, request_id):
        return self._sch.get(int(request_id))

    def decide_schedule_change(self, *, request_id, status, decided_by, admin_note=None):
        req = self._sch.get(int(request_id))
        if not req or req.status != RequestStatus.PENDING:
            return False
        self._sch[int(request_id)] = ScheduleChangeRequest(
            request_id=req.request_id,
            user_id=req.user_id,
            work_date=req.work_date,
            requested_shift_id=req.requested_shift_id,
            requested_note=req.requested_note,
            status=status,
            created_at=req.created_at,
            decided_by=int(decided_by),
            decided_at=datetime(2026, 2, 1, 11, 0, 0),
            admin_note=admin_note,
        )
        return True

    def list_schedule_change_requests(self, *, status=None, user_id=None, limit=200):
        return []


class FakeAttendanceRecord:
    def __init__(self):
        self.attendance_id = 10
        self.user_id = 2
        self.work_date = date(2026, 2, 1)
        self.check_in_time = datetime(2026, 2, 1, 8, 30)
        self.check_out_time = datetime(2026, 2, 1, 17, 30)
        self.status = AttendanceStatus.ON_TIME
        self.note = ""


class FakeAttendanceRepo:
    def __init__(self, record):
        self._record = record
        self.updated = None

    def get_for_user_and_date(self, user_id, work_date):
        if user_id == self._record.user_id and work_date == self._record.work_date:
            return self._record
        return None

    def admin_update_record(self, *, attendance_id, check_in_time, check_out_time, status, note=None):
        self.updated = {
            "attendance_id": attendance_id,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "status": status,
            "note": note,
        }
        return True


class FakeScheduleRepo:
    def __init__(self):
        self.upsert_called = None

    def upsert(self, *, user_id, work_date, shift_id, note=None):
        self.upsert_called = {
            "user_id": int(user_id),
            "work_date": work_date,
            "shift_id": int(shift_id),
            "note": note,
        }
        return 1


def test_staff_can_create_adjustment_when_record_exists():
    svc = RequestService(FakeRequestsRepo(), FakeAttendanceRepo(FakeAttendanceRecord()), FakeScheduleRepo())
    rid = svc.create_timesheet_adjustment(
        current_role=Role.STAFF,
        user_id=2,
        work_date=date(2026, 2, 1),
        requested_check_in="09:00",
        requested_check_out="",
        requested_note="Forgot to check in",
    )
    assert rid == 1


def test_non_staff_cannot_create_adjustment():
    svc = RequestService(FakeRequestsRepo(), FakeAttendanceRepo(FakeAttendanceRecord()), FakeScheduleRepo())
    with pytest.raises(AuthorizationError):
        svc.create_timesheet_adjustment(
            current_role=Role.ADMIN,
            user_id=2,
            work_date=date(2026, 2, 1),
            requested_check_in="09:00",
            requested_check_out="",
            requested_note="x",
        )


def test_admin_approving_adjustment_updates_attendance():
    req_repo = FakeRequestsRepo()
    attendance_repo = FakeAttendanceRepo(FakeAttendanceRecord())
    svc = RequestService(req_repo, attendance_repo, FakeScheduleRepo())

    rid = req_repo.create_timesheet_adjustment(
        user_id=2,
        work_date=date(2026, 2, 1),
        requested_check_in=time(9, 0),
        requested_check_out=None,
        requested_note="ok",
    )

    svc.approve_timesheet_adjustment(
        current_role=Role.ADMIN,
        admin_user_id=1,
        request_id=rid,
        admin_note="approved",
    )

    assert attendance_repo.updated is not None
    assert attendance_repo.updated["attendance_id"] == 10
    assert attendance_repo.updated["check_in_time"].hour == 9


def test_approve_fails_if_checkout_before_checkin():
    req_repo = FakeRequestsRepo()
    attendance_repo = FakeAttendanceRepo(FakeAttendanceRecord())
    svc = RequestService(req_repo, attendance_repo, FakeScheduleRepo())

    rid = req_repo.create_timesheet_adjustment(
        user_id=2,
        work_date=date(2026, 2, 1),
        requested_check_in=time(17, 0),
        requested_check_out=time(8, 0),
        requested_note=None,
    )

    with pytest.raises(ValidationError):
        svc.approve_timesheet_adjustment(
            current_role=Role.ADMIN,
            admin_user_id=1,
            request_id=rid,
        )


def test_staff_can_create_schedule_change_with_required_note():
    svc = RequestService(FakeRequestsRepo(), FakeAttendanceRepo(FakeAttendanceRecord()), FakeScheduleRepo())
    rid = svc.create_schedule_change(
        current_role=Role.STAFF,
        user_id=2,
        work_date=date(2026, 2, 2),
        requested_shift_id=1,
        requested_note="Đề xuất đổi ca do bận việc buổi sáng",
    )
    assert rid == 1


def test_admin_approving_schedule_change_applies_schedule():
    req_repo = FakeRequestsRepo()
    schedules_repo = FakeScheduleRepo()
    svc = RequestService(req_repo, FakeAttendanceRepo(FakeAttendanceRecord()), schedules_repo)

    rid = req_repo.create_schedule_change(
        user_id=2,
        work_date=date(2026, 2, 3),
        requested_shift_id=2,
        requested_note="Xin đổi ca chiều",
    )

    svc.approve_schedule_change(
        current_role=Role.ADMIN,
        admin_user_id=1,
        request_id=rid,
        admin_note="OK",
    )

    assert schedules_repo.upsert_called is not None
    assert schedules_repo.upsert_called["user_id"] == 2
    assert schedules_repo.upsert_called["shift_id"] == 2
