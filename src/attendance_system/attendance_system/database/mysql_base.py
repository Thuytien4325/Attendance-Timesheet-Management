from __future__ import annotations

from contextlib import contextmanager
from datetime import time, timedelta
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import mysql.connector

from .connection import DatabaseConnection


@contextmanager
def db_cursor(conn_factory: DatabaseConnection, *, dictionary: bool = True):
    conn = conn_factory.connect()
    try:
        cur = conn.cursor(dictionary=dictionary)
        try:
            yield conn, cur
            conn.commit()
        finally:
            cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetchone(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    return row if row else None


def fetchall(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall()
    return list(rows or [])


def normalize_mysql_time(value: Any) -> Optional[time]:
    """Normalize MySQL TIME values across connector implementations.

    mysql-connector can return TIME as:
    - datetime.time
    - datetime.timedelta
    - string (e.g. '08:30:00')
    """

    if value is None:
        return None

    if isinstance(value, time):
        return value

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds()) % 86400
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return time(hour=hours, minute=minutes, second=seconds)

    if isinstance(value, str):
        parts = value.strip().split(":")
        if len(parts) < 2:
            raise ValueError(f"Invalid time string: {value!r}")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) >= 3 and parts[2] else 0
        return time(hour=hours, minute=minutes, second=seconds)

    raise TypeError(f"Unsupported MySQL TIME value type: {type(value)!r}")
