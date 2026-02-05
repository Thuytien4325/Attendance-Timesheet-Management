import os
import urllib.parse


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "khoa_bi_mat_cua_nhom"

    # Cấu hình DB
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "38632347tT@")
    DB_HOST = os.environ.get("DB_HOST", os.environ.get("DB_HOST_ENV", "localhost"))
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))
    DB_NAME = os.environ.get("DB_NAME", os.environ.get("DB_DATABASE", "attendance_db"))

    # QR Code token for attendance check-in
    QR_TOKEN = os.environ.get("QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")

    # Dev helpers
    AUTO_INIT_DB = bool(int(os.environ.get("AUTO_INIT_DB", "0")))
    AUTO_SEED_DB = bool(int(os.environ.get("AUTO_SEED_DB", "0")))

    _encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{DB_USER}:{_encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# Compatibility with current app wiring (mysql-connector dict)
SECRET_KEY = Config.SECRET_KEY
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
