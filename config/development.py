import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "38632347tT@"),
    "database": os.getenv("DB_NAME", "attendance_db"),
}

# QR Code token for attendance check-in
QR_TOKEN = os.getenv("QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")

DEBUG = True

# If enabled, app will apply schema.sql on startup (idempotent: CREATE IF NOT EXISTS)
AUTO_INIT_DB = bool(int(os.getenv("AUTO_INIT_DB", "1")))
# Optional: also seed demo data on startup
AUTO_SEED_DB = bool(int(os.getenv("AUTO_SEED_DB", "0")))
