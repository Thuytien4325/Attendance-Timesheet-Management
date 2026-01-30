# File: app/models/attendance.py
from app.extensions import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    status = db.Column(db.String(50))
    notes = db.Column(db.Text)
    overtime_minutes = db.Column(db.Integer, default=0)
    approval_status = db.Column(db.String(20), default='Pending')
    manager_comment = db.Column(db.Text)
    user = db.relationship('User', backref='attendances')