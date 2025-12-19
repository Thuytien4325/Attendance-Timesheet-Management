import urllib.parse

# Khóa bí mật
SECRET_KEY = 'khoa_bi_mat_cua_nhom'

# Thông tin kết nối
db_user = 'root'
db_password = '38632347tT@'  # Mật khẩu gốc của bạn
db_host = 'localhost'
db_name = 'attendance_db'

# Mã hóa mật khẩu để xử lý ký tự '@' an toàn
encoded_password = urllib.parse.quote_plus(db_password)

# Chuỗi kết nối chuẩn cho SQLAlchemy
SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{db_user}:{encoded_password}@{db_host}/{db_name}'
SQLALCHEMY_TRACK_MODIFICATIONS = False