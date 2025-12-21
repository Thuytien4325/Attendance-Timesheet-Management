from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
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
import pandas as pd # Thêm thư viện xử lý Excel

app = Flask(__name__)
app.config.from_object(config)

# Giả lập CSRF token để tránh lỗi template
app.jinja_env.globals['csrf_token'] = lambda: ''

# Khởi tạo ORM
db = SQLAlchemy(app)

# ============================================================================
# 1. MODELS (OOP)
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

# ============================================================================
# 2. MIDDLEWARE
# ============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục!', 'warning')
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
# 3. CORE ROUTES
# ============================================================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect('/dashboard')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
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
    
    attendance_today = Attendance.query.filter_by(user_id=current_user.user_id, work_date=today).first()

    if current_user.role == 'admin':
        history_query = Attendance.query.order_by(Attendance.check_in_time.desc()).limit(50).all()
    else:
        history_query = Attendance.query.filter_by(user_id=current_user.user_id)\
                                        .order_by(Attendance.check_in_time.desc()).limit(30).all()
    
    formatted_data = []
    stats = {'total': len(history_query), 'on_time': 0, 'late': 0, 'early': 0}

    for att in history_query:
        if att.status in ['Đúng giờ', 'on_time']: stats['on_time'] += 1
        elif att.status in ['Đi muộn', 'late']: stats['late'] += 1
        elif att.status in ['Về sớm', 'early_leave']: stats['early'] += 1
        
        css_class = 'bg-secondary'
        if att.status in ['Đúng giờ', 'on_time']: css_class = 'bg-success'
        elif att.status in ['Đi muộn', 'late']: css_class = 'bg-danger'
        elif att.status in ['Về sớm', 'early_leave']: css_class = 'bg-warning text-dark'

        formatted_data.append({
            'full_name': att.user.full_name,
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

# ============================================================================
# 4. CHECK-IN / CHECK-OUT THỦ CÔNG
# ============================================================================
@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    user = User.query.get(session['user_id'])
    now = datetime.now()

    if Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first():
        flash('⚠️ Hôm nay bạn đã Check-in rồi!', 'warning')
        return redirect('/dashboard')

    if not user.shift:
        flash('❌ Chưa được xếp ca!', 'danger')
        return redirect('/dashboard')

    status, is_late, message = user.shift.get_checkin_status(now)
    msg_type = 'danger' if is_late else 'success'

    new_attendance = Attendance(
        user_id=user.user_id,
        work_date=now.date(),
        check_in_time=now,
        status=status,
        notes="Check-in Thủ công"
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

    new_status, message = user.shift.get_checkout_status(now, attendance.status)
    attendance.check_out_time = now
    attendance.status = new_status
    db.session.commit()

    flash(f"{message} lúc {now.strftime('%H:%M')}", 'success')
    return redirect('/dashboard')

# ============================================================================
# 5. QR CODE
# ============================================================================

@app.route('/my-qr')
@login_required
def my_qr():
    user = User.query.get(session['user_id'])
    qr_data = {
        'user_id': user.user_id,
        'username': user.username,
        'timestamp': datetime.now().isoformat()
    }
    return render_template('my_qr.html', user=user, qr_data_json=json.dumps(qr_data))

@app.route('/generate-qr')
@login_required
def generate_qr():
    user = User.query.get(session['user_id'])
    qr_data = {
        'user_id': user.user_id,
        'username': user.username,
        'timestamp': datetime.now().isoformat()
    }
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/scan')
def scan():
    return render_template('scan_qr.html')

@app.route('/scan-checkin', methods=['POST'])
def scan_checkin():
    try:
        data = request.get_json()
        qr_string = data.get('qr_data', '')
        
        if not qr_string:
            return jsonify({'success': False, 'message': 'Không có dữ liệu QR'}), 400
            
        try:
            qr_info = json.loads(qr_string)
            user_id = qr_info.get('user_id')
        except:
            return jsonify({'success': False, 'message': 'QR Code sai định dạng'}), 400
            
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Nhân viên không tồn tại'}), 404
            
        now = datetime.now()
        today = now.date()
        
        existing = Attendance.query.filter_by(user_id=user.user_id, work_date=today).first()
        if existing:
            return jsonify({
                'success': False, 
                'message': f'Xin chào {user.full_name}, bạn đã check-in rồi!',
                'user': {'full_name': user.full_name}
            }), 400
            
        if not user.shift:
            return jsonify({'success': False, 'message': 'Chưa được xếp ca làm việc'}), 400
            
        status, is_late, message = user.shift.get_checkin_status(now)
        
        new_attendance = Attendance(
            user_id=user.user_id,
            work_date=today,
            check_in_time=now,
            status=status,
            notes='Check-in qua QR Code'
        )
        db.session.add(new_attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Check-in thành công!',
            'user': {'full_name': user.full_name},
            'status': status,
            'time': now.strftime('%H:%M:%S'),
            'status_class': 'success' if status == 'Đúng giờ' else 'danger'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500

# ============================================================================
# 6. FACE ID (Khuôn mặt)
# ============================================================================

@app.route('/register-face', methods=['GET', 'POST'])
@login_required
def register_face():
    if request.method == 'GET':
        return render_template('face_register.html')
    
    try:
        data = request.get_json()
        image_data = data['image']
        
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        image_np = np.frombuffer(binary_data, dtype=np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        boxes = face_recognition.face_locations(rgb_img)
        if len(boxes) == 0:
            return jsonify({'success': False, 'message': 'Không tìm thấy khuôn mặt!'})
        if len(boxes) > 1:
            return jsonify({'success': False, 'message': 'Chỉ được để 1 khuôn mặt trước camera!'})
            
        encoding = face_recognition.face_encodings(rgb_img, boxes)[0]
        
        user = User.query.get(session['user_id'])
        user.face_encoding = json.dumps(encoding.tolist())
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Đăng ký khuôn mặt thành công!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/face-checkin')
def face_checkin_page():
    return render_template('face_checkin.html')

@app.route('/api/face-checkin', methods=['POST'])
def api_face_checkin():
    try:
        data = request.get_json()
        image_data = data['image']
        
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        image_np = np.frombuffer(binary_data, dtype=np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        boxes = face_recognition.face_locations(rgb_img)
        if not boxes:
            return jsonify({'success': False, 'message': 'Đang tìm khuôn mặt...'})
            
        unknown_encoding = face_recognition.face_encodings(rgb_img, boxes)[0]
        
        users = User.query.filter(User.face_encoding != None).all()
        found_user = None
        
        for u in users:
            try:
                known_encoding = np.array(json.loads(u.face_encoding))
                matches = face_recognition.compare_faces([known_encoding], unknown_encoding, tolerance=0.5)
                if matches[0]:
                    found_user = u
                    break
            except: continue
        
        if not found_user:
            return jsonify({'success': False, 'message': 'Không nhận diện được nhân viên!'})
            
        now = datetime.now()
        today = now.date()
        
        existing = Attendance.query.filter_by(user_id=found_user.user_id, work_date=today).first()
        if existing:
             return jsonify({'success': False, 'message': f'Xin chào {found_user.full_name}, bạn đã check-in rồi!'})
             
        if not found_user.shift:
             return jsonify({'success': False, 'message': 'Chưa được xếp ca!'})
             
        status, is_late, message = found_user.shift.get_checkin_status(now)
        
        new_att = Attendance(
            user_id=found_user.user_id,
            work_date=today,
            check_in_time=now,
            status=status,
            notes="Check-in Face ID"
        )
        db.session.add(new_att)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Check-in thành công: {found_user.full_name}',
            'status': status,
            'time': now.strftime('%H:%M:%S')
        })

    except Exception as e:
        return jsonify({'success': False, 'message': 'Lỗi hệ thống'})

# ==================================================
# 7. ADMIN ROUTES & EXPORT EXCEL
# ==================================================
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
    
    Attendance.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa thành công'})

# --- ROUTE XUẤT EXCEL (ĐÃ BỔ SUNG ĐỂ SỬA LỖI BUILDERROR) ---
@app.route('/admin/export_attendance')
@admin_required 
def export_attendance():
    try:
        # Lấy toàn bộ dữ liệu chấm công, Join bảng để lấy tên và phòng ban
        query = db.session.query(
            Attendance.work_date,
            User.full_name,
            Department.dept_name,
            Attendance.check_in_time,
            Attendance.check_out_time,
            Attendance.status,
            Attendance.notes
        ).join(User, Attendance.user_id == User.user_id)\
         .outerjoin(Department, User.dept_id == Department.dept_id)\
         .order_by(Attendance.work_date.desc())

        # Chuyển thành DataFrame của Pandas
        data = pd.DataFrame(query.all(), columns=['Ngày', 'Họ Tên', 'Phòng Ban', 'Giờ Vào', 'Giờ Ra', 'Trạng Thái', 'Ghi Chú'])
        
        # Format lại cột thời gian cho đẹp (bỏ giây thừa)
        data['Giờ Vào'] = pd.to_datetime(data['Giờ Vào']).dt.strftime('%H:%M:%S')
        data['Giờ Ra'] = pd.to_datetime(data['Giờ Ra']).dt.strftime('%H:%M:%S')

        # Xuất ra file Excel trong bộ nhớ (không lưu xuống ổ cứng)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            data.to_excel(writer, index=False, sheet_name='Báo Cáo')
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"Bang_Cham_Cong_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
        )
    except Exception as e:
        flash(f"Lỗi xuất file: {str(e)}", "danger")
        return redirect(url_for('admin_users'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)