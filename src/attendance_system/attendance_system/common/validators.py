from __future__ import annotations

from ..core.exceptions import ValidationError


def require_non_empty(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValidationError(f"{field_name} không hợp lệ")
    return value.strip()


def require_min_length(value: str, field_name: str, min_len: int) -> str:
    if value is None or len(value) < min_len:
        raise ValidationError(f"{field_name} tối thiểu {min_len} ký tự")
    return value
