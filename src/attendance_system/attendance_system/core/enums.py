from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """Vai trò người dùng dùng cho phân quyền."""

    ADMIN = "admin"
    STAFF = "staff"


class AttendanceStatus(str, Enum):
    """Trạng thái chấm công chuẩn hoá lưu trong CSDL."""

    ON_TIME = "ON_TIME"
    LATE = "LATE"
    EARLY_LEAVE = "EARLY_LEAVE"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class RequestStatus(str, Enum):
    """Trạng thái luồng duyệt yêu cầu (nghỉ phép/điều chỉnh/đổi lịch)."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
