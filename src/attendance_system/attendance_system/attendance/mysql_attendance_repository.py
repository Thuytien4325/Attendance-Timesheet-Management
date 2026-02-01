from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Sequence

from ..core.enums import AttendanceStatus
from ..database.connection import DatabaseConnection
from ..database.mysql_base import db_cursor, fetchall, fetchone
from .model import AttendanceRecord, AttendanceReportRow
from .repository import AttendanceRepository


class MySQLAttendanceRepository(AttendanceRepository):
    def __init__(self, conn_factory: DatabaseConnection):
        self._conn_factory = conn_factory

    def get_recent_for_user(self, user_id: int, limit: int) -> Sequence[AttendanceRecord]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT attendance_id, user_id, work_date, check_in_time, check_out_time, status, note
                FROM attendance_records
                WHERE user_id=%s
                ORDER BY work_date DESC
                LIMIT %s
                """,
                (user_id, int(limit)),
            )
            rows = fetchall(cur)
            return [
                AttendanceRecord(
                    attendance_id=int(r["attendance_id"]),
                    user_id=int(r["user_id"]),
                    work_date=r["work_date"],
                    check_in_time=r["check_in_time"],
                    check_out_time=r.get("check_out_time"),
                    status=AttendanceStatus(r["status"]),
                    note=r.get("note"),
                )
                for r in rows
            ]

    def get_for_user_and_date(self, user_id: int, work_date: date) -> Optional[AttendanceRecord]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT attendance_id, user_id, work_date, check_in_time, check_out_time, status, note
                FROM attendance_records
                WHERE user_id=%s AND work_date=%s
                """,
                (user_id, work_date),
            )
            r = fetchone(cur)
            if not r:
                return None
            return AttendanceRecord(
                attendance_id=int(r["attendance_id"]),
                user_id=int(r["user_id"]),
                work_date=r["work_date"],
                check_in_time=r["check_in_time"],
                check_out_time=r.get("check_out_time"),
                status=AttendanceStatus(r["status"]),
                note=r.get("note"),
            )

    def create_checkin(
        self,
        *,
        user_id: int,
        work_date: date,
        check_in_time: datetime,
        status: AttendanceStatus,
        note: Optional[str] = None,
    ) -> int:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                INSERT INTO attendance_records(user_id, work_date, check_in_time, status, note)
                VALUES(%s,%s,%s,%s,%s)
                """,
                (user_id, work_date, check_in_time, status.value, note),
            )
            return int(cur.lastrowid)

    def update_checkout(
        self,
        *,
        attendance_id: int,
        check_out_time: datetime,
        status: AttendanceStatus,
        note: Optional[str] = None,
    ) -> bool:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                UPDATE attendance_records
                SET check_out_time=%s, status=%s, note=%s
                WHERE attendance_id=%s
                """,
                (check_out_time, status.value, note, attendance_id),
            )
            return cur.rowcount > 0

    def admin_update_record(
        self,
        *,
        attendance_id: int,
        check_in_time: datetime,
        check_out_time: Optional[datetime],
        status: AttendanceStatus,
        note: Optional[str] = None,
    ) -> bool:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                UPDATE attendance_records
                SET check_in_time=%s, check_out_time=%s, status=%s, note=%s
                WHERE attendance_id=%s
                """,
                (check_in_time, check_out_time, status.value, note, int(attendance_id)),
            )
            return cur.rowcount > 0

    def get_report_rows(
        self,
        *,
        start_date: date,
        end_date: date,
        dept_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Sequence[AttendanceReportRow]:
        clauses = ["ar.work_date BETWEEN %s AND %s"]
        params: list[object] = [start_date, end_date]

        if dept_id is not None:
            clauses.append("u.dept_id=%s")
            params.append(int(dept_id))
        if user_id is not None:
            clauses.append("u.user_id=%s")
            params.append(int(user_id))

        where = " AND ".join(clauses)

        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                f"""
                SELECT
                    u.user_id, u.full_name, u.username,
                    d.dept_name,
                    s.shift_name, COALESCE(s.break_minutes, 0) AS break_minutes,
                    ar.work_date, ar.check_in_time, ar.check_out_time, ar.status, ar.note
                FROM attendance_records ar
                JOIN users u ON u.user_id = ar.user_id
                LEFT JOIN departments d ON d.dept_id = u.dept_id
                LEFT JOIN schedules sc ON sc.user_id = u.user_id AND sc.work_date = ar.work_date
                LEFT JOIN shifts s ON s.shift_id = COALESCE(sc.shift_id, u.shift_id)
                WHERE {where}
                ORDER BY ar.work_date DESC, u.user_id ASC
                """,
                tuple(params),
            )
            rows = fetchall(cur)

            return [
                AttendanceReportRow(
                    user_id=int(r["user_id"]),
                    full_name=r["full_name"],
                    username=r["username"],
                    dept_name=r.get("dept_name"),
                    shift_name=r.get("shift_name"),
                    break_minutes=int(r.get("break_minutes") or 0),
                    work_date=r["work_date"],
                    check_in_time=r["check_in_time"],
                    check_out_time=r.get("check_out_time"),
                    status=AttendanceStatus(r["status"]),
                    note=r.get("note"),
                )
                for r in rows
            ]
