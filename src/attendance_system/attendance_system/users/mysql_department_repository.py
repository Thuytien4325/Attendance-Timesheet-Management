from __future__ import annotations

from typing import Sequence

from ..database.connection import DatabaseConnection
from ..database.mysql_base import db_cursor, fetchall
from .department_model import Department
from .department_repository import DepartmentRepository


class MySQLDepartmentRepository(DepartmentRepository):
    def __init__(self, conn_factory: DatabaseConnection):
        self._conn_factory = conn_factory

    def list_all(self) -> Sequence[Department]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_name")
            rows = fetchall(cur)
            return [Department(dept_id=int(r["dept_id"]), dept_name=r["dept_name"]) for r in rows]
