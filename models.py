from extensions import db

class Department(db.Model):
    __tablename__ = 'departments'
    
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100), nullable=False)

    # Quan hệ: Một phòng ban có nhiều nhân viên
    users = db.relationship('User', backref='department', lazy=True)


class Shift(db.Model):
    __tablename__ = 'shifts'
    
    shift_id = db.Column(db.Integer, primary_key=True)
    shift_name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    late_grace_period = db.Column(db.Integer, default=15)       # phút đi muộn cho phép
    early_leave_threshold = db.Column(db.Integer, default=30)   # phút về sớm cho phép

    # Quan hệ: Một loại ca có thể áp dụng cho nhiều nhân viên (mặc định)
    users = db.relationship('User', backref='shift', lazy=True)


class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='staff')  # staff / manager / admin

    dept_id = db.Column(db.Integer, db.ForeignKey('departments.dept_id'))
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.shift_id')) # Ca mặc định

    face_encoding = db.Column(db.Text)  # Lưu dữ liệu khuôn mặt phục vụ FaceID


class EmployeeSchedule(db.Model):
    """
    Bảng lưu lịch làm việc linh hoạt (Roster).
    Dùng khi nhân viên làm ca không cố định theo tuần/tháng.
    """
    __tablename__ = 'employee_schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.shift_id'), nullable=True) # Null = Nghỉ (OFF)
    work_date = db.Column(db.Date, nullable=False)
    
    # Quan hệ để truy xuất thông tin nhanh
    shift = db.relationship('Shift')
    user = db.relationship('User', backref='schedules')


class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)

    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)

    status = db.Column(db.String(50))  # Đúng giờ / Đi muộn / Về sớm / Vắng
    notes = db.Column(db.Text)
    
    #-- Tăng ca ---
    overtime_minutes = db.Column(db.Integer, default=0) 
    
    # --- PHÊ DUYỆT CHẤM CÔNG ---
    approval_status = db.Column(db.String(20), default='Pending')  # Pending / Approved / Rejected
    manager_comment = db.Column(db.Text)

    user = db.relationship('User', backref='attendances')