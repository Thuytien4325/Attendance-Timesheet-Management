from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional, Sequence

from ..core.enums import RequestStatus
from ..database.connection import DatabaseConnection
from ..database.mysql_base import db_cursor, fetchall, fetchone
from .model import LeaveRequest, ScheduleChangeRequest, TimesheetAdjustmentRequest
from .repository import RequestRepository


class MySQLRequestRepository(RequestRepository):
    def __init__(self, conn_factory: DatabaseConnection):
        self._conn_factory = conn_factory

    # -------- Timesheet adjustments --------
    def create_timesheet_adjustment(
        self,
        *,
        user_id: int,
        work_date: date,
        requested_check_in: Optional[time],
        requested_check_out: Optional[time],
        requested_note: Optional[str],
    ) -> int:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                INSERT INTO timesheet_adjustment_requests(
                    user_id, work_date, requested_check_in, requested_check_out, requested_note, status
                )
                VALUES(%s,%s,%s,%s,%s,%s)
                """,
                (
                    int(user_id),
                    work_date,
                    requested_check_in,
                    requested_check_out,
                    requested_note,
                    RequestStatus.PENDING.value,
                ),
            )
            return int(cur.lastrowid)

    def get_timesheet_adjustment(self, *, request_id: int) -> Optional[TimesheetAdjustmentRequest]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT request_id, user_id, work_date,
                       requested_check_in, requested_check_out, requested_note,
                       status, created_at, decided_by, decided_at, admin_note
                FROM timesheet_adjustment_requests
                WHERE request_id=%s
                """,
                (int(request_id),),
            )
            r = fetchone(cur)
            if not r:
                return None
            return TimesheetAdjustmentRequest(
                request_id=int(r["request_id"]),
                user_id=int(r["user_id"]),
                work_date=r["work_date"],
                requested_check_in=r.get("requested_check_in"),
                requested_check_out=r.get("requested_check_out"),
                requested_note=r.get("requested_note"),
                status=RequestStatus(r["status"]),
                created_at=r["created_at"],
                decided_by=r.get("decided_by"),
                decided_at=r.get("decided_at"),
                admin_note=r.get("admin_note"),
            )

    def list_timesheet_adjustments(
        self,
        *,
        status: Optional[RequestStatus] = None,
        user_id: Optional[int] = None,
        limit: int = 200,
    ) -> Sequence[dict]:
        clauses = ["1=1"]
        params: list[object] = []

        if status is not None:
            clauses.append("r.status=%s")
            params.append(status.value)
        if user_id is not None:
            clauses.append("r.user_id=%s")
            params.append(int(user_id))

        where = " AND ".join(clauses)

        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                f"""
                SELECT r.request_id, r.user_id, u.full_name, u.username,
                       r.work_date, r.requested_check_in, r.requested_check_out,
                       r.requested_note, r.status, r.created_at,
                       r.decided_by, r.decided_at, r.admin_note
                FROM timesheet_adjustment_requests r
                JOIN users u ON u.user_id = r.user_id
                WHERE {where}
                ORDER BY r.created_at DESC
                LIMIT %s
                """,
                tuple(params + [int(limit)]),
            )
            rows = fetchall(cur)
            out: list[dict] = []
            for r in rows:
                out.append(
                    {
                        "request_id": int(r["request_id"]),
                        "user_id": int(r["user_id"]),
                        "full_name": r["full_name"],
                        "username": r["username"],
                        "work_date": r["work_date"].strftime("%Y-%m-%d"),
                        "requested_check_in": (r.get("requested_check_in").strftime("%H:%M") if r.get("requested_check_in") else "-"),
                        "requested_check_out": (r.get("requested_check_out").strftime("%H:%M") if r.get("requested_check_out") else "-"),
                        "requested_note": r.get("requested_note") or "",
                        "status": r["status"],
                        "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M"),
                        "admin_note": r.get("admin_note") or "",
                    }
                )
            return out

    def decide_timesheet_adjustment(
        self,
        *,
        request_id: int,
        status: RequestStatus,
        decided_by: int,
        admin_note: Optional[str] = None,
    ) -> bool:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                UPDATE timesheet_adjustment_requests
                SET status=%s, decided_by=%s, decided_at=NOW(), admin_note=%s
                WHERE request_id=%s AND status=%s
                """,
                (
                    status.value,
                    int(decided_by),
                    admin_note,
                    int(request_id),
                    RequestStatus.PENDING.value,
                ),
            )
            return cur.rowcount > 0

    # -------- Leave requests --------
    def create_leave(self, *, user_id: int, start_date: date, end_date: date, reason: str) -> int:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                INSERT INTO leave_requests(user_id, start_date, end_date, reason, status)
                VALUES(%s,%s,%s,%s,%s)
                """,
                (int(user_id), start_date, end_date, reason, RequestStatus.PENDING.value),
            )
            return int(cur.lastrowid)

    def list_leave_requests(
        self,
        *,
        status: Optional[RequestStatus] = None,
        user_id: Optional[int] = None,
        limit: int = 200,
    ) -> Sequence[dict]:
        clauses = ["1=1"]
        params: list[object] = []

        if status is not None:
            clauses.append("r.status=%s")
            params.append(status.value)
        if user_id is not None:
            clauses.append("r.user_id=%s")
            params.append(int(user_id))

        where = " AND ".join(clauses)

        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                f"""
                SELECT r.request_id, r.user_id, u.full_name, u.username,
                       r.start_date, r.end_date, r.reason,
                       r.status, r.created_at, r.admin_note
                FROM leave_requests r
                JOIN users u ON u.user_id = r.user_id
                WHERE {where}
                ORDER BY r.created_at DESC
                LIMIT %s
                """,
                tuple(params + [int(limit)]),
            )
            rows = fetchall(cur)
            out: list[dict] = []
            for r in rows:
                out.append(
                    {
                        "request_id": int(r["request_id"]),
                        "user_id": int(r["user_id"]),
                        "full_name": r["full_name"],
                        "username": r["username"],
                        "start_date": r["start_date"].strftime("%Y-%m-%d"),
                        "end_date": r["end_date"].strftime("%Y-%m-%d"),
                        "reason": r["reason"],
                        "status": r["status"],
                        "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M"),
                        "admin_note": r.get("admin_note") or "",
                    }
                )
            return out

    def decide_leave(
        self,
        *,
        request_id: int,
        status: RequestStatus,
        decided_by: int,
        admin_note: Optional[str] = None,
    ) -> bool:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                UPDATE leave_requests
                SET status=%s, decided_by=%s, decided_at=NOW(), admin_note=%s
                WHERE request_id=%s AND status=%s
                """,
                (
                    status.value,
                    int(decided_by),
                    admin_note,
                    int(request_id),
                    RequestStatus.PENDING.value,
                ),
            )
            return cur.rowcount > 0

    # -------- Schedule change requests --------
    def create_schedule_change(
        self,
        *,
        user_id: int,
        work_date: date,
        requested_shift_id: int,
        requested_note: str,
    ) -> int:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                INSERT INTO schedule_change_requests(
                    user_id, work_date, requested_shift_id, requested_note, status
                )
                VALUES(%s,%s,%s,%s,%s)
                """,
                (
                    int(user_id),
                    work_date,
                    int(requested_shift_id),
                    requested_note,
                    RequestStatus.PENDING.value,
                ),
            )
            return int(cur.lastrowid)

    def get_schedule_change(self, *, request_id: int) -> Optional[ScheduleChangeRequest]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT request_id, user_id, work_date,
                       requested_shift_id, requested_note,
                       status, created_at, decided_by, decided_at, admin_note
                FROM schedule_change_requests
                WHERE request_id=%s
                """,
                (int(request_id),),
            )
            r = fetchone(cur)
            if not r:
                return None
            return ScheduleChangeRequest(
                request_id=int(r["request_id"]),
                user_id=int(r["user_id"]),
                work_date=r["work_date"],
                requested_shift_id=int(r["requested_shift_id"]),
                requested_note=r["requested_note"],
                status=RequestStatus(r["status"]),
                created_at=r["created_at"],
                decided_by=r.get("decided_by"),
                decided_at=r.get("decided_at"),
                admin_note=r.get("admin_note"),
            )

    def list_schedule_change_requests(
        self,
        *,
        status: Optional[RequestStatus] = None,
        user_id: Optional[int] = None,
        limit: int = 200,
    ) -> Sequence[dict]:
        clauses = ["1=1"]
        params: list[object] = []

        if status is not None:
            clauses.append("r.status=%s")
            params.append(status.value)
        if user_id is not None:
            clauses.append("r.user_id=%s")
            params.append(int(user_id))

        where = " AND ".join(clauses)

        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                f"""
                SELECT r.request_id, r.user_id, u.full_name, u.username,
                       r.work_date, r.requested_shift_id, r.requested_note,
                       r.status, r.created_at, r.admin_note,
                       s.shift_name, s.start_time, s.end_time
                FROM schedule_change_requests r
                JOIN users u ON u.user_id = r.user_id
                JOIN shifts s ON s.shift_id = r.requested_shift_id
                WHERE {where}
                ORDER BY r.created_at DESC
                LIMIT %s
                """,
                tuple(params + [int(limit)]),
            )
            rows = fetchall(cur)
            out: list[dict] = []
            for r in rows:
                out.append(
                    {
                        "request_id": int(r["request_id"]),
                        "user_id": int(r["user_id"]),
                        "full_name": r["full_name"],
                        "username": r["username"],
                        "work_date": r["work_date"].strftime("%Y-%m-%d"),
                        "requested_shift_id": int(r["requested_shift_id"]),
                        "requested_shift": f"{r['shift_name']} ({str(r['start_time'])[:5]}-{str(r['end_time'])[:5]})",
                        "requested_note": r["requested_note"],
                        "status": r["status"],
                        "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M"),
                        "admin_note": r.get("admin_note") or "",
                    }
                )
            return out

    def decide_schedule_change(
        self,
        *,
        request_id: int,
        status: RequestStatus,
        decided_by: int,
        admin_note: Optional[str] = None,
    ) -> bool:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                UPDATE schedule_change_requests
                SET status=%s, decided_by=%s, decided_at=NOW(), admin_note=%s
                WHERE request_id=%s AND status=%s
                """,
                (
                    status.value,
                    int(decided_by),
                    admin_note,
                    int(request_id),
                    RequestStatus.PENDING.value,
                ),
            )
            return cur.rowcount > 0
