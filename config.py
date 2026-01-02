import os
import urllib.parse

class Config:
    # 1. Cấu hình bảo mật Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'khoa_bi_mat_cua_nhom'

    # 2. Thông tin kết nối Database
    DB_USER = 'root'
    DB_PASSWORD = '38632347tT@'  # Mật khẩu gốc chứa ký tự đặc biệt '@'
    DB_HOST = 'localhost'
    DB_NAME = 'attendance_db'

    # 3. Xử lý mã hóa mật khẩu (Bắt buộc vì mật khẩu có chứa '@')
    # urllib.parse.quote_plus sẽ chuyển '@' thành '%40' để không bị nhầm với cú pháp URL
    _encoded_password = urllib.parse.quote_plus(DB_PASSWORD)

    # 4. Chuỗi kết nối SQLAlchemy hoàn chỉnh
    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{_encoded_password}@{DB_HOST}/{DB_NAME}'
    
    # Tắt tính năng theo dõi thay đổi object không cần thiết (tiết kiệm tài nguyên)
    SQLALCHEMY_TRACK_MODIFICATIONS = False