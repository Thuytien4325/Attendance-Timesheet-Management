from __future__ import annotations

import sys
from pathlib import Path

import importlib

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import get_settings_module

from src.attendance_system.attendance_system.database.bootstrap import apply_schema, list_tables


def main() -> None:
    settings = importlib.import_module(get_settings_module())
    db_config = dict(settings.DB_CONFIG)

    schema_path = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
    apply_schema(db_config, schema_path=schema_path)
    tables = list_tables(db_config)
    print(
        "OK: Applied schema.sql -> "
        f"{db_config.get('user')}@{db_config.get('host')}:{db_config.get('port', 3306)}/{db_config.get('database')} "
        f"(tables={len(tables)})"
    )


if __name__ == "__main__":
    main()
