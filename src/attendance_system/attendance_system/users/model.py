from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.enums import Role


@dataclass(frozen=True)
class User:
    """Thực thể miền (domain): User.

    Lưu ý: Đây là đối tượng dữ liệu thuần (không chứa code truy cập DB).
    """

    user_id: int
    full_name: str
    username: str
    password_hash: str
    role: Role
    dept_id: Optional[int]
    shift_id: Optional[int]
    is_active: bool = True
