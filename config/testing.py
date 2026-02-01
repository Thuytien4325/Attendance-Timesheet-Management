import os

SECRET_KEY = "test-secret"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "12345"),
    "database": os.getenv("DB_NAME", "attendance_db"),
}

DEBUG = False
TESTING = True

AUTO_INIT_DB = bool(int(os.getenv("AUTO_INIT_DB", "0")))
AUTO_SEED_DB = bool(int(os.getenv("AUTO_SEED_DB", "0")))
