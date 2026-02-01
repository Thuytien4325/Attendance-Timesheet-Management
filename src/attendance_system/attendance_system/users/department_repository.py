from __future__ import annotations

from typing import Protocol, Sequence

from .department_model import Department


class DepartmentRepository(Protocol):
    def list_all(self) -> Sequence[Department]:
        raise NotImplementedError
