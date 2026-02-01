from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Department:
    dept_id: int
    dept_name: str
