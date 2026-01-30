# File: app/models/user.py
from app.extensions import db
from flask_login import UserMixin

# 1. Class Department
class Department(db.Model):
    __tablename__ = 'departments'
    __table_args__ = {'extend_existing': True}
    
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100), nullable=False)
    
    # Quan hệ
    users = db.relationship('User', backref='department', lazy=True)

# 2. Class User (Đây là cái Python đang tìm kiếm mà không thấy)
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}  # <--- THÊM DÒNG NÀY VÀO ĐÂY
    
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='staff') # staff / manager / admin

    dept_id = db.Column(db.Integer, db.ForeignKey('departments.dept_id'))
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.shift_id')) 

    face_encoding = db.Column(db.Text) # Dữ liệu khuôn mặt

    # Hàm bắt buộc cho Flask-Login
    def get_id(self):
        return str(self.user_id)