from __future__ import annotations

import importlib
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from config import get_settings_module

from .database.bootstrap import apply_schema, apply_seed_sql, ensure_demo_users, list_tables

from .container import build_container
from .attendance.controller import register as register_attendance
from .schedules.controller import register as register_schedules
from .users.controller import register as register_users
from .requests.controller import register as register_requests


def create_app() -> Flask:
    load_dotenv(override=False)
    app = Flask(__name__, template_folder="../../../templates", static_folder="../../../static")

    settings_module = get_settings_module()
    settings = importlib.import_module(settings_module)
    app.secret_key = getattr(settings, "SECRET_KEY")
    db_config = getattr(settings, "DB_CONFIG")
    app.config["DEBUG"] = bool(getattr(settings, "DEBUG", False))
    app.config["QR_TOKEN"] = getattr(settings, "QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")

    # Helpful startup info to avoid "DBeaver connected but no tables" confusion.
    if app.config["DEBUG"]:
        print(
            "[attendance-system] settings=", settings_module,
            " db=", f"{db_config.get('user')}@{db_config.get('host')}:{db_config.get('port', 3306)}/{db_config.get('database')}"
        )

    auto_init_db = bool(getattr(settings, "AUTO_INIT_DB", False))
    auto_seed_db = bool(getattr(settings, "AUTO_SEED_DB", False))
    if auto_init_db:
        schema_path = Path(__file__).resolve().parents[3] / "database" / "schema.sql"
        apply_schema(db_config, schema_path=schema_path)
        if app.config["DEBUG"]:
            print(f"[attendance-system] schema ready (tables={len(list_tables(db_config))})")
    if auto_seed_db:
        seed_path = Path(__file__).resolve().parents[3] / "database" / "seed.sql"
        apply_seed_sql(db_config, seed_path=seed_path)
        ensure_demo_users(db_config)
        if app.config["DEBUG"]:
            print("[attendance-system] demo seed ready")

    container = build_container(db_config=db_config)

    register_users(app, container)
    register_attendance(app, container)
    register_schedules(app, container)
    register_requests(app, container)

    return app
