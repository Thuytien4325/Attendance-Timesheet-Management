from __future__ import annotations

from typing import Optional, Sequence

from ..database.connection import DatabaseConnection
from ..database.mysql_base import db_cursor, fetchall, fetchone, normalize_mysql_time
from .model import Shift
from .repository import ShiftRepository


class MySQLShiftRepository(ShiftRepository):
    def __init__(self, conn_factory: DatabaseConnection):
        self._conn_factory = conn_factory

    def list_all(self) -> Sequence[Shift]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT shift_id, shift_name, start_time, end_time, break_minutes
                FROM shifts
                ORDER BY shift_id
                """
            )
            rows = fetchall(cur)
            return [
                Shift(
                    shift_id=int(r["shift_id"]),
                    shift_name=r["shift_name"],
                    start_time=normalize_mysql_time(r["start_time"]),
                    end_time=normalize_mysql_time(r["end_time"]),
                    break_minutes=int(r.get("break_minutes") or 0),
                )
                for r in rows
            ]

    def get_by_id(self, shift_id: int) -> Optional[Shift]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT shift_id, shift_name, start_time, end_time, break_minutes
                FROM shifts
                WHERE shift_id=%s
                """,
                (shift_id,),
            )
            r = fetchone(cur)
            if not r:
                return None
            return Shift(
                shift_id=int(r["shift_id"]),
                shift_name=r["shift_name"],
                start_time=normalize_mysql_time(r["start_time"]),
                end_time=normalize_mysql_time(r["end_time"]),
                break_minutes=int(r.get("break_minutes") or 0),
            )
