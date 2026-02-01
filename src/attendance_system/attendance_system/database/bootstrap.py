from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import mysql.connector
from werkzeug.security import generate_password_hash


@dataclass(frozen=True)
class DBTarget:
    host: str
    port: int
    user: str
    password: str
    database: str


def _as_target(db_config: dict) -> DBTarget:
    return DBTarget(
        host=str(db_config.get("host", "localhost")),
        port=int(db_config.get("port", 3306)),
        user=str(db_config.get("user", "root")),
        password=str(db_config.get("password", "")),
        database=str(db_config.get("database", "attendance_db")),
    )


def _strip_create_db_and_use(sql: str) -> str:
    # Keep schema.sql compatible regardless of DB name.
    sql = re.sub(r"(?im)^\s*CREATE\s+DATABASE\b.*?;\s*$", "", sql)
    sql = re.sub(r"(?im)^\s*USE\b.*?;\s*$", "", sql)
    return sql


def _iter_sql_statements(sql: str) -> Iterable[str]:
    # Minimal SQL splitter for schema/seed files (handles ';' inside quotes).
    buf: list[str] = []
    in_single = False
    in_double = False
    escape = False

    for ch in sql:
        if escape:
            buf.append(ch)
            escape = False
            continue

        if ch == "\\":
            buf.append(ch)
            escape = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            continue

        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            buf.clear()
            if stmt:
                yield stmt
            continue

        buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        yield tail


def _exec_sql(cur, sql: str) -> None:
    for stmt in _iter_sql_statements(sql):
        cur.execute(stmt)


def ensure_database_exists(db_config: dict) -> None:
    target = _as_target(db_config)
    conn = mysql.connector.connect(
        host=target.host,
        port=target.port,
        user=target.user,
        password=target.password,
        use_pure=True,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{target.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        conn.commit()
    finally:
        conn.close()


def apply_schema(db_config: dict, *, schema_path: str | Path) -> None:
    target = _as_target(db_config)
    ensure_database_exists(db_config)

    schema_path = Path(schema_path)
    sql = _strip_create_db_and_use(schema_path.read_text(encoding="utf-8"))

    conn = mysql.connector.connect(
        host=target.host,
        port=target.port,
        user=target.user,
        password=target.password,
        database=target.database,
        use_pure=True,
    )
    try:
        cur = conn.cursor()
        _exec_sql(cur, sql)
        conn.commit()
    finally:
        conn.close()


def apply_seed_sql(db_config: dict, *, seed_path: str | Path) -> None:
    target = _as_target(db_config)
    seed_path = Path(seed_path)
    sql = _strip_create_db_and_use(seed_path.read_text(encoding="utf-8"))

    conn = mysql.connector.connect(
        host=target.host,
        port=target.port,
        user=target.user,
        password=target.password,
        database=target.database,
        use_pure=True,
    )
    try:
        cur = conn.cursor()
        _exec_sql(cur, sql)
        conn.commit()
    finally:
        conn.close()


def ensure_demo_users(db_config: dict) -> None:
    target = _as_target(db_config)

    conn = mysql.connector.connect(
        host=target.host,
        port=target.port,
        user=target.user,
        password=target.password,
        database=target.database,
        use_pure=True,
    )
    try:
        cur = conn.cursor(dictionary=True)

        id_col_map = {
            "departments": "dept_id",
            "shifts": "shift_id",
            "users": "user_id",
        }

        def get_id(table: str, col: str, value: str) -> int:
            id_col = id_col_map.get(table)
            if not id_col:
                raise RuntimeError(f"Unsupported lookup table: {table}")
            cur.execute(f"SELECT {id_col} AS id FROM {table} WHERE {col}=%s", (value,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Missing {table} row for {col}={value}")
            return int(row["id"])

        dept_it = get_id("departments", "dept_name", "IT")
        dept_hr = get_id("departments", "dept_name", "HR")
        shift_hc = get_id("shifts", "shift_name", "Hành chính")
        shift_cs = get_id("shifts", "shift_name", "Ca sáng")

        def upsert_user(full_name: str, username: str, password: str, role: str, dept_id: int, shift_id: int) -> None:
            password_hash = generate_password_hash(password)
            cur.execute("SELECT user_id FROM users WHERE username=%s", (username,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE users
                    SET full_name=%s, password_hash=%s, role=%s, dept_id=%s, shift_id=%s, is_active=1
                    WHERE username=%s
                    """,
                    (full_name, password_hash, role, dept_id, shift_id, username),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO users (full_name, username, password_hash, role, dept_id, shift_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (full_name, username, password_hash, role, dept_id, shift_id),
                )

        upsert_user("Admin Demo", "admin", "admin123", "admin", dept_it, shift_hc)
        upsert_user("Nguyễn Văn A", "nguyenvana", "staff123", "staff", dept_hr, shift_cs)

        # Migrate any legacy 'user' roles to 'staff' (the system no longer supports role='user').
        cur.execute("UPDATE users SET role='staff' WHERE role='user'")

        conn.commit()
    finally:
        conn.close()


def list_tables(db_config: dict) -> list[str]:
    target = _as_target(db_config)
    conn = mysql.connector.connect(
        host=target.host,
        port=target.port,
        user=target.user,
        password=target.password,
        database=target.database,
        use_pure=True,
    )
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
