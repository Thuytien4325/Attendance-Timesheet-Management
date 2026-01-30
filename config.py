# File: config.py
import os
import urllib.parse

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'khoa_bi_mat_cua_nhom'
    
    # Cấu hình DB
    DB_USER = 'root'
    DB_PASSWORD = '38632347tT@'
    DB_HOST = os.environ.get('DB_HOST_ENV', 'localhost')
    DB_NAME = 'attendance_db'

    _encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{_encoded_password}@{DB_HOST}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False