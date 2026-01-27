import os
import urllib.parse

class Config:
    # 1. Cấu hình bảo mật Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'khoa_bi_mat_cua_nhom'

    # 2. Thông tin kết nối Database
    DB_USER = 'root'
    DB_PASSWORD = '38632347tT@'  # Mật khẩu gốc chứa ký tự đặc biệt
    
    # --- PHẦN QUAN TRỌNG ĐÃ SỬA (AUTO-SWITCH) ---
    # Logic: Tìm xem có biến môi trường từ Docker không?
    # - Nếu có (Đang chạy Docker) -> Dùng 'host.docker.internal'
    # - Nếu không (Đang chạy trên máy) -> Tự động quay về 'localhost'
    DB_HOST = os.environ.get('DB_HOST_ENV', 'localhost')
    
    DB_NAME = 'attendance_db'

    # 3. Xử lý mã hóa mật khẩu
    _encoded_password = urllib.parse.quote_plus(DB_PASSWORD)

    # 4. Chuỗi kết nối SQLAlchemy hoàn chỉnh
    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{_encoded_password}@{DB_HOST}/{DB_NAME}'
    
    # Tắt tính năng theo dõi thay đổi object không cần thiết
    SQLALCHEMY_TRACK_MODIFICATIONS = False