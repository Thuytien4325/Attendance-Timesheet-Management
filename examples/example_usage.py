"""Ví dụ: dùng service layer (không qua Flask).

Mục tiêu: minh hoạ SOLID/OOP - Controllers chỉ là lớp mỏng, nghiệp vụ nằm ở Services.
"""

import importlib

from config import get_settings_module

from src.attendance_system.attendance_system.container import build_container


def main():
    settings = importlib.import_module(get_settings_module())
    container = build_container(db_config=settings.DB_CONFIG)
    print(container.attendance_service.get_history_ui(user_id=1, limit=5))


if __name__ == "__main__":
    main()
