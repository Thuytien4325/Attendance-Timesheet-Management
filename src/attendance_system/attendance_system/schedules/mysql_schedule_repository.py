from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from ..database.connection import DatabaseConnection
from ..database.mysql_base import db_cursor, fetchall, fetchone
from .model import Schedule
from .repository import ScheduleRepository


class MySQLScheduleRepository(ScheduleRepository):
    def __init__(self, conn_factory: DatabaseConnection):
        self._conn_factory = conn_factory

    def get_for_user_and_date(self, *, user_id: int, work_date: date) -> Optional[Schedule]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT schedule_id, user_id, work_date, shift_id, note
                FROM schedules
                WHERE user_id=%s AND work_date=%s
                """,
                (user_id, work_date),
            )
            r = fetchone(cur)
            if not r:
                return None
            return Schedule(
                schedule_id=int(r["schedule_id"]),
                user_id=int(r["user_id"]),
                work_date=r["work_date"],
                shift_id=int(r["shift_id"]),
                note=r.get("note"),
            )

    def upsert(self, *, user_id: int, work_date: date, shift_id: int, note: Optional[str] = None) -> int:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                INSERT INTO schedules(user_id, work_date, shift_id, note)
                VALUES(%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE shift_id=VALUES(shift_id), note=VALUES(note)
                """,
                (int(user_id), work_date, int(shift_id), note),
            )

            # If it was an update, lastrowid can be 0; fetch schedule_id.
            if cur.lastrowid:
                return int(cur.lastrowid)

            cur.execute("SELECT schedule_id FROM schedules WHERE user_id=%s AND work_date=%s", (int(user_id), work_date))
            r = fetchone(cur)
            return int(r["schedule_id"]) if r else 0

    def delete(self, *, schedule_id: int) -> bool:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute("DELETE FROM schedules WHERE schedule_id=%s", (int(schedule_id),))
            return cur.rowcount > 0

    def list_range(self, *, start: date, end: date, user_id: Optional[int] = None) -> Sequence[dict]:
        clauses = ["sc.work_date BETWEEN %s AND %s"]
        params: list[object] = [start, end]
        if user_id is not None:
            clauses.append("u.user_id=%s")
            params.append(int(user_id))

        where = " AND ".join(clauses)

        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                f"""
                SELECT
                    sc.schedule_id,
                    sc.work_date,
                    u.user_id,
                    u.full_name,
                    u.username,
                    s.shift_id,
                    s.shift_name,
                    s.start_time,
                    s.end_time,
                    sc.note
                FROM schedules sc
                JOIN users u ON u.user_id = sc.user_id
                JOIN shifts s ON s.shift_id = sc.shift_id
                WHERE {where}
                ORDER BY sc.work_date ASC, u.user_id ASC
                """,
                tuple(params),
            )
            rows = fetchall(cur)
            out: list[dict] = []
            for r in rows:
                out.append(
                    {
                        "schedule_id": int(r["schedule_id"]),
                        "work_date": r["work_date"].strftime("%Y-%m-%d"),
                        "user_id": int(r["user_id"]),
                        "full_name": r["full_name"],
                        "username": r["username"],
                        "shift_id": int(r["shift_id"]),
                        "shift": f"{r['shift_name']} ({str(r['start_time'])[:5]}-{str(r['end_time'])[:5]})",
                        "note": r.get("note") or "",
                    }
                )
            return out
