<<<<<<< HEAD
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
=======
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
>>>>>>> ef805d5bb9b9721a12e0ee6b221ec469d2816d01
from functools import wraps
from datetime import datetime, timedelta, date
import config

app = Flask(__name__)
app.config.from_object(config)

# --- KHẮC PHỤC LỖI 1: 'csrf_token' is undefined ---
# Dòng này giúp template không bị lỗi khi tìm biến csrf_token
app.jinja_env.globals['csrf_token'] = lambda: ''

# Khởi tạo ORM
db = SQLAlchemy(app)

# ============================================================================
# 1. MODELS (CÁC LỚP ĐỐI TƯỢNG - OOP)
# ============================================================================

class Department(db.Model):
    __tablename__ = 'departments'
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100), nullable=False)
    users = db.relationship('User', backref='department', lazy=True)

class Shift(db.Model):
    __tablename__ = 'shifts'
    shift_id = db.Column(db.Integer, primary_key=True)
    shift_name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    late_grace_period = db.Column(db.Integer, default=15)
    early_leave_threshold = db.Column(db.Integer, default=30)
    users = db.relationship('User', backref='shift', lazy=True)

    # [OOP METHOD] Logic tính toán trạng thái Check-in
    def get_checkin_status(self, checkin_time):
        shift_start_dt = datetime.combine(checkin_time.date(), self.start_time)
        allowed_limit = shift_start_dt + timedelta(minutes=self.late_grace_period)

        if checkin_time <= allowed_limit:
            return 'Đúng giờ', False, f"✅ Check-in thành công lúc {checkin_time.strftime('%H:%M')}"
        else:
            late_minutes = int((checkin_time - shift_start_dt).total_seconds() / 60)
            return 'Đi muộn', True, f"⏰ Check-in muộn {late_minutes} phút lúc {checkin_time.strftime('%H:%M')}"

    # [OOP METHOD] Logic tính toán Check-out
    def get_checkout_status(self, checkout_time, current_status):
        shift_end_dt = datetime.combine(checkout_time.date(), self.end_time)
        early_threshold = shift_end_dt - timedelta(minutes=self.early_leave_threshold)

        if checkout_time < early_threshold:
            early_minutes = int((shift_end_dt - checkout_time).total_seconds() / 60)
            return 'Về sớm', f"⚠️ Về sớm {early_minutes} phút"
        
        final_status = current_status if current_status == 'Đi muộn' else 'Đúng giờ'
        return final_status, "✅ Hoàn thành ca làm việc"

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='staff')
    dept_id = db.Column(db.Integer, db.ForeignKey('departments.dept_id'))
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.shift_id'))

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False) # Cột này bắt buộc có dữ liệu
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    status = db.Column(db.String(50))
    
    # Quan hệ để lấy thông tin user từ bảng attendance (attendance.user.full_name)
    user = db.relationship('User', backref='attendances')

# ============================================================================
# 2. MIDDLEWARE
# ============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect('/')
        if session.get('role') != 'admin':
            return render_template('403.html', current_user=session), 403
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# 3. ROUTES
# ============================================================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect('/dashboard')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # [OOP] Tìm user bằng ORM
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.user_id
            session['name'] = user.full_name
            session['role'] = user.role
            
            if user.shift:
                s_time = user.shift.start_time.strftime('%H:%M')
                e_time = user.shift.end_time.strftime('%H:%M')
                session['shift_info'] = f"{user.shift.shift_name} ({s_time}-{e_time})"
            else:
                session['shift_info'] = "Chưa xếp ca"
            
            flash('Đăng nhập thành công!', 'success')
            return redirect('/dashboard')
        else:
            flash('Sai thông tin đăng nhập!', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
@login_required 
def dashboard():
    current_user = User.query.get(session['user_id'])
    today = date.today()
    
    # 1. Trạng thái hôm nay
    attendance_today = Attendance.query.filter_by(user_id=current_user.user_id, work_date=today).first()

    # 2. Lấy lịch sử (Admin thấy hết, Staff thấy mình)
    if current_user.role == 'admin':
        # [OOP] Join ngầm định nhờ relationship
        history_query = Attendance.query.order_by(Attendance.check_in_time.desc()).limit(50).all()
    else:
        history_query = Attendance.query.filter_by(user_id=current_user.user_id)\
                                        .order_by(Attendance.check_in_time.desc()).limit(30).all()
    
    # 3. Format dữ liệu
    formatted_data = []
    stats = {'total': 0, 'on_time': 0, 'late': 0, 'early': 0}
    stats['total'] = len(history_query)

    for att in history_query:
        # Thống kê
        if att.status in ['Đúng giờ', 'on_time']: stats['on_time'] += 1
        elif att.status in ['Đi muộn', 'late']: stats['late'] += 1
        elif att.status in ['Về sớm', 'early_leave']: stats['early'] += 1
        
        css_class = 'bg-secondary'
        if att.status in ['Đúng giờ', 'on_time']: css_class = 'bg-success'
        elif att.status in ['Đi muộn', 'late']: css_class = 'bg-danger'
        elif att.status in ['Về sớm', 'early_leave']: css_class = 'bg-warning text-dark'

        formatted_data.append({
            'full_name': att.user.full_name, # [OOP] Lấy tên từ bảng User qua quan hệ
            'date': att.check_in_time.strftime('%d/%m/%Y'),
            'check_in': att.check_in_time.strftime('%H:%M'),
            'check_out': att.check_out_time.strftime('%H:%M') if att.check_out_time else '--:--',
            'status': att.status,
            'css_class': css_class
        })

    return render_template('dashboard.html', 
                           attendance_today=attendance_today,
                           stats=stats,
                           data=formatted_data,
                           shift=current_user.shift)

@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    user = User.query.get(session['user_id'])
    now = datetime.now()

    # 1. Kiểm tra trùng
    if Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first():
        flash('⚠️ Hôm nay bạn đã Check-in rồi!', 'warning')
        return redirect('/dashboard')

    if not user.shift:
        flash('❌ Chưa được xếp ca!', 'danger')
        return redirect('/dashboard')

    # 2. Tính toán trạng thái bằng Method của Shift
    status, is_late, message = user.shift.get_checkin_status(now)
    msg_type = 'danger' if is_late else 'success'

    # 3. Lưu vào DB (OOP)
    # --- KHẮC PHỤC LỖI 2: Field 'work_date' doesn't have a default value ---
    new_attendance = Attendance(
        user_id=user.user_id,
        work_date=now.date(),  # <-- QUAN TRỌNG: Phải truyền work_date vào đây
        check_in_time=now,
        status=status
    )
    
    db.session.add(new_attendance)
    db.session.commit()

    flash(message, msg_type)
    return redirect('/dashboard')

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    user = User.query.get(session['user_id'])
    now = datetime.now()

    attendance = Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first()

    if not attendance:
        flash('⚠️ Chưa Check-in!', 'warning')
        return redirect('/dashboard')
    
    if attendance.check_out_time:
        flash('⚠️ Đã Check-out rồi!', 'warning')
        return redirect('/dashboard')

    # Tính toán
    new_status, message = user.shift.get_checkout_status(now, attendance.status)
    msg_type = 'warning' if new_status == 'Về sớm' else 'success'

    # Cập nhật Object
    attendance.check_out_time = now
    attendance.status = new_status
    db.session.commit()

    flash(f"{message} lúc {now.strftime('%H:%M')}", msg_type)
    return redirect('/dashboard')

# --- ADMIN ROUTES (OOP) ---
@app.route('/admin/users')
@admin_required
def admin_users():
    users_list = User.query.order_by(User.user_id.desc()).all()
    view_data = []
    for u in users_list:
        view_data.append({
            'user_id': u.user_id,
            'full_name': u.full_name,
            'username': u.username,
            'role': u.role,
            'dept_name': u.department.dept_name if u.department else 'Chưa xếp',
            'shift_name': u.shift.shift_name if u.shift else 'Chưa xếp'
        })
    return render_template('admin/admin_users.html', users=view_data)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        fullname = request.form['fullName']
        username = request.form['username']
        password = request.form['password']
        dept_id = request.form['department']
        shift_id = request.form['shift']
        
        if User.query.filter_by(username=username).first():
            flash('Username đã tồn tại!', 'danger')
        else:
            new_user = User(full_name=fullname, username=username, password=password, 
                            dept_id=dept_id, shift_id=shift_id, role='staff')
            db.session.add(new_user)
            db.session.commit()
            flash('Thêm nhân viên thành công!', 'success')
            return redirect('/admin/add_user')

    depts = Department.query.all()
    shifts = Shift.query.all()
    return render_template('admin/add_employee.html', departments=depts, shifts=shifts)

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user: return jsonify({'success': False, 'message': 'Không tồn tại'})
    if user.role == 'admin': return jsonify({'success': False, 'message': 'Không thể xóa Admin'})
    
    # Xóa lịch sử điểm danh trước (nếu cần thiết để tránh lỗi khóa ngoại)
    Attendance.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa thành công'})


# ==================================================
# 7. CHỨC NĂNG BỔ SUNG: EXPORT EXCEL (PHONG CÁCH OOP)
# ==================================================
class AttendanceExcelExporter:
    """Lớp xử lý logic truy vấn và xuất file Excel chuyên nghiệp"""
    
    def __init__(self, db_config):
        import pandas as pd
        from sqlalchemy import create_engine
        self.pd = pd
        # Khởi tạo engine kết nối hỗ trợ UTF-8 để không lỗi font tiếng Việt
        db_uri = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}?charset=utf8mb4"
        self.engine = create_engine(db_uri)

    def get_full_data(self):
        """Truy vấn dữ liệu kết hợp thông tin nhân viên và phòng ban"""
        query = """
            SELECT 
                a.id AS 'ID',
                u.full_name AS 'Họ và Tên',
                d.dept_name AS 'Phòng ban',
                a.check_in_time AS 'Giờ vào',
                a.check_out_time AS 'Giờ ra',
                a.status AS 'Trạng thái'
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            LEFT JOIN departments d ON u.dept_id = d.dept_id
            ORDER BY a.check_in_time DESC
        """
        return self.pd.read_sql(query, self.engine)

    def export(self):
        """Tạo luồng dữ liệu file .xlsx (In-memory stream)"""
        import io
        df = self.get_full_data()
        output = io.BytesIO()
        # Xuất file Excel với định dạng chuẩn
        with self.pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Báo cáo công')
        output.seek(0)
        return output

@app.route('/admin/export_attendance')
@admin_required 
def export_attendance():
    try:
        # Sử dụng lớp AttendanceExcelExporter để xử lý (OOP)
        exporter = AttendanceExcelExporter(config.DB_CONFIG)
        excel_stream = exporter.export()
        
        # Gửi file về trình duyệt để tải xuống
        return send_file(
            excel_stream,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"Bao_cao_diem_danh_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
    except Exception as e:
        flash(f"Lỗi khi xuất file: {str(e)}", "danger")
        return redirect(url_for('admin_users'))

# --- DI CHUYỂN LỆNH CHẠY APP XUỐNG DƯỚI CÙNG ĐỂ NHẬN DIỆN ĐỦ ROUTE ---
if __name__ == '__main__':
    app.run(debug=True)
