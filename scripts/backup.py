"""Backup database.

Note: Script này ưu tiên dùng `mysqldump` (nếu máy có cài).
Nếu không có,có thể backup bằng tool MySQL Workbench hoặc phpMyAdmin.
"""

from __future__ import annotations

import importlib
import subprocess
from datetime import datetime
from pathlib import Path

from config import get_settings_module


def main() -> None:
    settings = importlib.import_module(get_settings_module())
    db = settings.DB_CONFIG

    out_dir = Path(__file__).resolve().parents[1] / "backups"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"attendance_db_{ts}.sql"

    cmd = [
        "mysqldump",
        f"-h{db['host']}",
        f"-u{db['user']}",
        f"-p{db['password']}",
        db["database"],
    ]

    try:
        with out_file.open("wb") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)
        print(f"OK: Backup created: {out_file}")
    except FileNotFoundError:
        raise SystemExit("Không tìm thấy `mysqldump`. Hãy cài MySQL client tools hoặc backup bằng Workbench.")


if __name__ == "__main__":
    main()
