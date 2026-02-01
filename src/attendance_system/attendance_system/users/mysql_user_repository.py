from __future__ import annotations

from typing import Optional, Sequence

from ..core.enums import Role
from ..database.connection import DatabaseConnection
from ..database.mysql_base import db_cursor, fetchall, fetchone
from .model import User
from .repository import UserRepository


class MySQLUserRepository(UserRepository):
    def __init__(self, conn_factory: DatabaseConnection):
        self._conn_factory = conn_factory

    def get_by_id(self, user_id: int) -> Optional[User]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT user_id, full_name, username, password_hash, role, dept_id, shift_id, is_active
                FROM users
                WHERE user_id=%s
                """,
                (user_id,),
            )
            row = fetchone(cur)
            if not row:
                return None
            return User(
                user_id=int(row["user_id"]),
                full_name=row["full_name"],
                username=row["username"],
                password_hash=row["password_hash"],
                role=Role(row["role"]),
                dept_id=row.get("dept_id"),
                shift_id=row.get("shift_id"),
                is_active=bool(row.get("is_active", True)),
            )

    def get_by_username(self, username: str) -> Optional[User]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT user_id, full_name, username, password_hash, role, dept_id, shift_id, is_active
                FROM users
                WHERE username=%s
                """,
                (username,),
            )
            row = fetchone(cur)
            if not row:
                return None
            return User(
                user_id=int(row["user_id"]),
                full_name=row["full_name"],
                username=row["username"],
                password_hash=row["password_hash"],
                role=Role(row["role"]),
                dept_id=row.get("dept_id"),
                shift_id=row.get("shift_id"),
                is_active=bool(row.get("is_active", True)),
            )

    def create_user(
        self,
        *,
        full_name: str,
        username: str,
        password_hash: str,
        role: Role,
        dept_id: int,
        shift_id: int,
    ) -> int:
        with db_cursor(self._conn_factory) as (conn, cur):
            cur.execute(
                """
                INSERT INTO users(full_name, username, password_hash, role, dept_id, shift_id, is_active)
                VALUES(%s,%s,%s,%s,%s,%s,1)
                """,
                (full_name, username, password_hash, role.value, dept_id, shift_id),
            )
            return int(cur.lastrowid)

    def delete_by_id(self, user_id: int) -> bool:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
            return cur.rowcount > 0

    def list_admin_view(self) -> Sequence[dict]:
        with db_cursor(self._conn_factory) as (_, cur):
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.username, u.role,
                       d.dept_name,
                       s.shift_name, s.start_time, s.end_time
                FROM users u
                LEFT JOIN departments d ON d.dept_id = u.dept_id
                LEFT JOIN shifts s ON s.shift_id = u.shift_id
                ORDER BY u.user_id DESC
                """
            )
            rows = fetchall(cur)
            out: list[dict] = []
            for r in rows:
                out.append(
                    {
                        "user_id": r["user_id"],
                        "full_name": r["full_name"],
                        "username": r["username"],
                        "role": r["role"],
                        "dept_name": r.get("dept_name") or "-",
                        "shift": (
                            f"{r.get('shift_name')} ({str(r.get('start_time'))[:5]}-{str(r.get('end_time'))[:5]})"
                            if r.get("shift_name")
                            else "-"
                        ),
                    }
                )
            return out
