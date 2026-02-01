import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "38632347tT@"),
    "database": os.getenv("DB_NAME", "attendance_db"),
}

DEBUG = True

AUTO_INIT_DB = True
AUTO_SEED_DB = False
