from __future__ import annotations

from typing import Optional, Protocol, Sequence

from ..core.enums import Role
from .model import User


class UserRepository(Protocol):
    """Giao diện repository cho User.

    Lưu ý (DIP): tầng service phụ thuộc vào interface này, không phụ thuộc trực tiếp DB cụ thể.
    """

    def get_by_id(self, user_id: int) -> Optional[User]:
        raise NotImplementedError

    def get_by_username(self, username: str) -> Optional[User]:
        raise NotImplementedError

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
        raise NotImplementedError

    def delete_by_id(self, user_id: int) -> bool:
        raise NotImplementedError

    def set_active(self, user_id: int, *, is_active: bool) -> bool:
        raise NotImplementedError

    def list_admin_view(self) -> Sequence[dict]:
        raise NotImplementedError
