from __future__ import annotations

from typing import Optional, Protocol, Sequence

from .model import Shift


class ShiftRepository(Protocol):
    def list_all(self) -> Sequence[Shift]:
        raise NotImplementedError

    def get_by_id(self, shift_id: int) -> Optional[Shift]:
        raise NotImplementedError
