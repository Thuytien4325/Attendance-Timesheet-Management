import os

SECRET_KEY = os.getenv("SECRET_KEY", "please-set-SECRET_KEY")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "38632347tT@"),
    "database": os.getenv("DB_NAME", "attendance_db"),
}

# QR Code token for attendance check-in
QR_TOKEN = os.getenv("QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")

DEBUG = False

AUTO_INIT_DB = bool(int(os.getenv("AUTO_INIT_DB", "0")))
AUTO_SEED_DB = bool(int(os.getenv("AUTO_SEED_DB", "0")))
