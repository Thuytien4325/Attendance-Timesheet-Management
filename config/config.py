import os
import urllib.parse


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "khoa_bi_mat_cua_nhom"

    # Cấu hình DB
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "123456")
    DB_HOST = os.environ.get("DB_HOST", os.environ.get("DB_HOST_ENV", "localhost"))
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))
    DB_NAME = os.environ.get("DB_NAME", os.environ.get("DB_DATABASE", "attendance_db"))

    # Dev helpers
    AUTO_INIT_DB = bool(int(os.environ.get("AUTO_INIT_DB", "0")))
    AUTO_SEED_DB = bool(int(os.environ.get("AUTO_SEED_DB", "0")))

    _encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{DB_USER}:{_encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# Compatibility with current app wiring (mysql-connector dict)
SECRET_KEY = Config.SECRET_KEY
DB_CONFIG = {
    "host": Config.DB_HOST,
    "port": Config.DB_PORT,
    "user": Config.DB_USER,
    "password": Config.DB_PASSWORD,
    "database": Config.DB_NAME,
}

DEBUG = bool(int(os.environ.get("DEBUG", "1")))

AUTO_INIT_DB = Config.AUTO_INIT_DB
AUTO_SEED_DB = Config.AUTO_SEED_DB
