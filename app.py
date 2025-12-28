from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from functools import wraps
from datetime import datetime, timedelta, date
import config
import qrcode
import io
import json
import face_recognition
import numpy as np
import base64
import cv2
import pandas as pd

app = Flask(__name__)
app.config.from_object(config)

# Fix lỗi CSRF cho template
app.jinja_env.globals['csrf_token'] = lambda: ''

db = SQLAlchemy(app)

# ==================================================
# 1. MODELS
# ==================================================
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

    def get_checkin_status(self, checkin_time):
        shift_start_dt = datetime.combine(checkin_time.date(), self.start_time)
        allowed_limit = shift_start_dt + timedelta(minutes=self.late_grace_period)
        if checkin_time <= allowed_limit:
            return 'Đúng giờ', False, f"✅ Check-in thành công lúc {checkin_time.strftime('%H:%M')}"
        else:
            late_minutes = int((checkin_time - shift_start_dt).total_seconds() / 60)
            return 'Đi muộn', True, f"⏰ Muộn {late_minutes} phút"

    def get_checkout_status(self, checkout_time, current_status):
        shift_end_dt = datetime.combine(checkout_time.date(), self.end_time)
        early_threshold = shift_end_dt - timedelta(minutes=self.early_leave_threshold)
        if checkout_time < early_threshold:
            return 'Về sớm', f"⚠️ Về sớm lúc {checkout_time.strftime('%H:%M')}"
        
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
    face_encoding = db.Column(db.Text) 

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    status = db.Column(db.String(50))
    notes = db.Column(db.Text)
    user = db.relationship('User', backref='attendances')

# ==================================================
# 2. MIDDLEWARE & AUTH ROUTES
# ==================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect('/')
        if session.get('role') != 'admin': return render_template('403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect('/dashboard')
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if user:
            session['user_id'] = user.user_id
            session['name'] = user.full_name
            session['role'] = user.role
            session['shift_info'] = f"{user.shift.shift_name}" if user.shift else "Chưa xếp ca"
            flash('Đăng nhập thành công!', 'success')
            return redirect('/dashboard')
        flash('Sai thông tin!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ==================================================
# 3. DASHBOARD & CHECKIN LOGIC
# ==================================================
@app.route('/dashboard')
@login_required 
def dashboard():
    user = User.query.get(session['user_id'])
    today = date.today()
    att_today = Attendance.query.filter_by(user_id=user.user_id, work_date=today).first()

    # Lấy lịch sử
    query = Attendance.query
    if user.role != 'admin':
        query = query.filter_by(user_id=user.user_id)
    history = query.order_by(Attendance.check_in_time.desc()).limit(50).all()
    
    # Format dữ liệu hiển thị
    data = []
    stats = {'total': len(history), 'on_time': 0, 'late': 0, 'early': 0}
    
    for row in history:
        st = row.status.lower() if row.status else ""
        if 'đúng' in st or 'on_time' in st: stats['on_time'] += 1
        elif 'muộn' in st or 'late' in st: stats['late'] += 1
        elif 'sớm' in st or 'early' in st: stats['early'] += 1
        
        css = 'bg-secondary'
        if 'đúng' in st: css = 'bg-success'
        elif 'muộn' in st: css = 'bg-danger'
        elif 'sớm' in st: css = 'bg-warning text-dark'

        data.append({
            'full_name': row.user.full_name,
            'date': row.check_in_time.strftime('%d/%m/%Y'),
            'check_in': row.check_in_time.strftime('%H:%M'),
            'check_out': row.check_out_time.strftime('%H:%M') if row.check_out_time else '--:--',
            'status': row.status,
            'css_class': css
        })

    return render_template('dashboard.html', attendance_today=att_today, stats=stats, data=data, shift=user.shift)

@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    user = User.query.get(session['user_id'])
    now = datetime.now()
    if Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first():
        flash('Đã check-in rồi!', 'warning')
        return redirect('/dashboard')
    
    if not user.shift:
        flash('Chưa xếp ca!', 'danger')
        return redirect('/dashboard')

    status, is_late, msg = user.shift.get_checkin_status(now)
    
    new_att = Attendance(
        user_id=user.user_id, 
        work_date=now.date(), 
        check_in_time=now, 
        status=status, 
        notes="Thủ công"
    )
    db.session.add(new_att)
    db.session.commit()
    flash(msg, 'danger' if is_late else 'success')
    return redirect('/dashboard')

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    user = User.query.get(session['user_id'])
    now = datetime.now()
    att = Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first()
    
    if not att:
        flash('Chưa check-in!', 'warning')
        return redirect('/dashboard')
    if att.check_out_time:
        flash('Đã check-out!', 'warning')
        return redirect('/dashboard')

    status, msg = user.shift.get_checkout_status(now, att.status)
    att.check_out_time = now
    att.status = status
    db.session.commit()
    flash(msg, 'success')
    return redirect('/dashboard')

# ==================================================
# 4. API THỐNG KÊ (CHO BIỂU ĐỒ)
# ==================================================
@app.route('/api/stats')
@login_required
def api_stats():
    if session.get('role') != 'admin': return jsonify({'success': False}), 403
    try:
        today = date.today()
        # Biểu đồ tròn
        counts = db.session.query(Attendance.status, func.count(Attendance.id)).filter(Attendance.work_date == today).group_by(Attendance.status).all()
        pie = {'on_time': 0, 'late': 0, 'early': 0}
        for s, c in counts:
            st = s.lower()
            if 'đúng' in st: pie['on_time'] += c
            elif 'muộn' in st: pie['late'] += c
            elif 'sớm' in st: pie['early'] += c
            
        # Biểu đồ cột
        week_ago = today - timedelta(days=6)
        daily = db.session.query(Attendance.work_date, func.count(Attendance.id)).filter(Attendance.work_date >= week_ago).group_by(Attendance.work_date).all()
        bar_labels, bar_data = [], []
        temp = {d[0]: d[1] for d in daily}
        
        for i in range(7):
            d = week_ago + timedelta(days=i)
            bar_labels.append(d.strftime('%d/%m'))
            bar_data.append(temp.get(d, 0))
            
        return jsonify({'success': True, 'pie': pie, 'bar': {'labels': bar_labels, 'data': bar_data}})
    except Exception as e: return jsonify({'success': False, 'message': str(e)}), 500

# ==================================================
# 5. QR CODE & FACE ID ROUTES
# ==================================================
@app.route('/my-qr')
@login_required
def my_qr():
    user = User.query.get(session['user_id'])
    data = {'user_id': user.user_id, 'ts': str(datetime.now())}
    return render_template('my_qr.html', user=user, qr_data_json=json.dumps(data))

@app.route('/generate-qr')
@login_required
def generate_qr():
    user = User.query.get(session['user_id'])
    data = {'user_id': user.user_id, 'ts': str(datetime.now())}
    img = qrcode.make(json.dumps(data))
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/scan')
def scan(): return render_template('scan_qr.html')

@app.route('/scan-checkin', methods=['POST'])
def scan_checkin():
    try:
        data = request.get_json()
        info = json.loads(data.get('qr_data', '{}'))
        user = User.query.get(info.get('user_id'))
        if not user: return jsonify({'success': False, 'message': 'Không tìm thấy NV'}), 404
        
        now = datetime.now()
        if Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first():
            return jsonify({'success': False, 'message': 'Đã chấm công rồi!'}), 400
            
        status, _, _ = user.shift.get_checkin_status(now)
        # Thêm class màu cho frontend
        status_class = 'success' if 'Đúng' in status else 'danger'
        
        db.session.add(Attendance(user_id=user.user_id, work_date=now.date(), check_in_time=now, status=status, notes="QR Code"))
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Thành công', 
            'user': {'full_name': user.full_name}, 
            'status': status, 
            'status_class': status_class,
            'shift_name': user.shift.shift_name if user.shift else "Chưa xếp",
            'time': now.strftime('%H:%M')
        })
    except Exception as e: 
        print(f"Lỗi Scan QR: {e}")
        return jsonify({'success': False, 'message': 'Lỗi QR'}), 500

@app.route('/register-face', methods=['GET', 'POST'])
@login_required
def register_face():
    if request.method == 'GET': return render_template('face_register.html')
    try:
        data = request.get_json()
        img_bytes = base64.b64decode(data['image'].split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # --- FIX 1: Xử lý đa dạng định dạng ảnh (PNG, v.v.) ---
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img is None:
            return jsonify({'success': False, 'message': 'Ảnh không hợp lệ'})

        # Xử lý RGBA (4 kênh màu) -> BGR
        if len(img.shape) == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        # Xử lý Grayscale (1 kênh màu) -> BGR
        elif len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # Chuyển sang RGB và ép kiểu contiguous cho dlib
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        # -----------------------------------------------------
        
        boxes = face_recognition.face_locations(rgb)
        if not boxes: return jsonify({'success': False, 'message': 'Không thấy mặt'})
        
        enc = face_recognition.face_encodings(rgb, boxes)[0]
        user = User.query.get(session['user_id'])
        user.face_encoding = json.dumps(enc.tolist())
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đăng ký thành công'})
    except Exception as e: 
        print(f"Lỗi Register Face: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/face-checkin')
def face_checkin_page(): return render_template('face_checkin.html')

@app.route('/api/face-checkin', methods=['POST'])
def api_face_checkin():
    try:
        data = request.get_json()
        img_bytes = base64.b64decode(data['image'].split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # --- FIX 2: Xử lý đa dạng định dạng ảnh (Tương tự ở trên) ---
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img is None:
            return jsonify({'success': False, 'message': 'Ảnh lỗi'})

        # Xử lý RGBA -> BGR
        if len(img.shape) == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        # Xử lý Grayscale -> BGR
        elif len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # Chuyển sang RGB và ép kiểu
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        # ------------------------------------------------------------
        
        boxes = face_recognition.face_locations(rgb)
        if not boxes: return jsonify({'success': False, 'message': 'Đang tìm mặt...'})
        
        unknown_enc = face_recognition.face_encodings(rgb, boxes)[0]
        users = User.query.filter(User.face_encoding != None).all()
        
        found = None
        for u in users:
            try:
                known = np.array(json.loads(u.face_encoding))
                if face_recognition.compare_faces([known], unknown_enc, tolerance=0.5)[0]:
                    found = u; break
            except: continue
        
        if not found: return jsonify({'success': False, 'message': 'Không nhận diện được'})
        
        now = datetime.now()
        if Attendance.query.filter_by(user_id=found.user_id, work_date=now.date()).first():
            return jsonify({'success': False, 'message': f'{found.full_name} đã chấm công!'})
            
        status, _, _ = found.shift.get_checkin_status(now)
        # Thêm class màu
        status_class = 'success' if 'Đúng' in status else 'danger'

        db.session.add(Attendance(user_id=found.user_id, work_date=now.date(), check_in_time=now, status=status, notes="FaceID"))
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Xin chào {found.full_name}', 
            'status': status, 
            'status_class': status_class,
            'time': now.strftime('%H:%M')
        })
    except Exception as e: 
        print(f"Lỗi Face Checkin: {e}")
        return jsonify({'success': False, 'message': 'Lỗi hệ thống'})

# ==================================================
# 6. ADMIN ROUTES
# ==================================================
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.user_id.desc()).all()
    data = [{'user_id': u.user_id, 'full_name': u.full_name, 'username': u.username, 'role': u.role, 'dept_name': u.department.dept_name if u.department else '', 'shift_name': u.shift.shift_name if u.shift else ''} for u in users]
    return render_template('admin/admin_users.html', users=data)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username tồn tại!', 'danger')
        else:
            u = User(full_name=request.form['fullName'], username=request.form['username'], password=request.form['password'], dept_id=request.form['department'], shift_id=request.form['shift'])
            db.session.add(u); db.session.commit()
            flash('Thêm thành công', 'success'); return redirect('/admin/add_user')
    return render_template('admin/add_employee.html', departments=Department.query.all(), shifts=Shift.query.all())

@app.route('/admin/user/delete/<int:id>', methods=['POST'])
@admin_required
def delete_user(id):
    u = User.query.get(id)
    if not u: return jsonify({'success': False, 'message': 'Không tìm thấy'})
    if u.role == 'admin': return jsonify({'success': False, 'message': 'Không xóa Admin'})
    Attendance.query.filter_by(user_id=id).delete()
    db.session.delete(u); db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/export_attendance')
@admin_required
def export_attendance():
    try:
        q = db.session.query(Attendance.work_date, User.full_name, Department.dept_name, Attendance.check_in_time, Attendance.check_out_time, Attendance.status, Attendance.notes).join(User).outerjoin(Department).all()
        df = pd.DataFrame(q, columns=['Ngày', 'Tên', 'Phòng', 'Vào', 'Ra', 'Trạng thái', 'Ghi chú'])
        
        # Format lại giờ
        df['Vào'] = pd.to_datetime(df['Vào']).dt.strftime('%H:%M:%S')
        df['Ra'] = pd.to_datetime(df['Ra']).dt.strftime('%H:%M:%S')
        
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
        out.seek(0)
        return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="BaoCao.xlsx")
    except Exception as e:
        flash(f"Lỗi xuất file: {e}", "danger")
        return redirect(url_for('admin_users'))

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)