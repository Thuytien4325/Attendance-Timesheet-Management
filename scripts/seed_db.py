from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import get_settings_module

from src.attendance_system.attendance_system.database.bootstrap import apply_seed_sql, ensure_demo_users


def main() -> None:
    settings = importlib.import_module(get_settings_module())
    db_config = dict(settings.DB_CONFIG)

    seed_path = Path(__file__).resolve().parents[1] / "database" / "seed.sql"
    apply_seed_sql(db_config, seed_path=seed_path)
    ensure_demo_users(db_config)

    print(
        "OK: Seeded database -> "
        f"{db_config.get('user')}@{db_config.get('host')}:{db_config.get('port', 3306)}/{db_config.get('database')}"
    )


if __name__ == "__main__":
    main()
