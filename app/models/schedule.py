# File: app/models/schedule.py
from app.extensions import db

class Shift(db.Model):
    __tablename__ = 'shifts'
    shift_id = db.Column(db.Integer, primary_key=True)
    shift_name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    late_grace_period = db.Column(db.Integer, default=15)
    early_leave_threshold = db.Column(db.Integer, default=30)
    users = db.relationship('User', backref='shift', lazy=True)

class EmployeeSchedule(db.Model):
    __tablename__ = 'employee_schedule'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.shift_id'), nullable=True)
    work_date = db.Column(db.Date, nullable=False)
    shift = db.relationship('Shift')
    user = db.relationship('User', backref='schedules')