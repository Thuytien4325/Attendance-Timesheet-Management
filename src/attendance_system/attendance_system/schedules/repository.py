from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, Sequence

from .model import Schedule


class ScheduleRepository(Protocol):
    def get_for_user_and_date(self, *, user_id: int, work_date: date) -> Optional[Schedule]:
        raise NotImplementedError

    def upsert(self, *, user_id: int, work_date: date, shift_id: int, note: Optional[str] = None) -> int:
        """Create or update a schedule assignment.

        Returns schedule_id.
        """

        raise NotImplementedError

    def delete(self, *, schedule_id: int) -> bool:
        raise NotImplementedError

    def list_range(self, *, start: date, end: date, user_id: Optional[int] = None) -> Sequence[dict]:
        """List schedules for UI table (joined with user/shift)."""

        raise NotImplementedError
