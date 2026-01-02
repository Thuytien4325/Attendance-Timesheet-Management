from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from sqlalchemy import func
from functools import wraps
from datetime import datetime, timedelta, date
import qrcode
import io
import json
import face_recognition
import numpy as np
import base64
import cv2
import pandas as pd

# --- IMPORT CÁC MODULE ĐÃ TÁCH (SOLID) ---
from config import Config
from extensions import db
from models import User, Shift, Department, Attendance
from services import TimekeepingService

app = Flask(__name__)
# Nạp cấu hình từ file config.py
app.config.from_object(Config)

# Khởi tạo DB
db.init_app(app)

# Fix lỗi CSRF cho giao diện
app.jinja_env.globals['csrf_token'] = lambda: ''

# ==================================================
# 1. MIDDLEWARE (Kiểm tra đăng nhập)
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

# ==================================================
# 2. AUTH ROUTES (Đăng nhập/Đăng xuất)
# ==================================================
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
        flash('Sai thông tin đăng nhập!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ==================================================
# 3. DASHBOARD (Trang chủ)
# ==================================================
@app.route('/dashboard')
@login_required 
def dashboard():
    user = User.query.get(session['user_id'])
    today = date.today()
    att_today = Attendance.query.filter_by(user_id=user.user_id, work_date=today).first()

    # Lấy lịch sử chấm công
    query = Attendance.query
    if user.role != 'admin':
        query = query.filter_by(user_id=user.user_id)
    history = query.order_by(Attendance.check_in_time.desc()).limit(50).all()
    
    # Xử lý dữ liệu hiển thị ra bảng
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

# ==================================================
# 4. CHỨC NĂNG CHẤM CÔNG (Gọi Service Logic)
# ==================================================
@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    user = User.query.get(session['user_id'])
    now = datetime.now()
    
    if Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first():
        flash('Hôm nay bạn đã Check-in rồi!', 'warning'); return redirect('/dashboard')
    
    if not user.shift:
        flash('Chưa được xếp ca làm việc!', 'danger'); return redirect('/dashboard')

    # [SOLID] Gọi Logic tính toán từ Service
    status, is_late, msg = TimekeepingService.calculate_checkin_status(now, user.shift)
    
    new_att = Attendance(user_id=user.user_id, work_date=now.date(), check_in_time=now, status=status, notes="Thủ công")
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
    
    if not att: flash('Chưa check-in!', 'warning'); return redirect('/dashboard')
    if att.check_out_time: flash('Đã check-out!', 'warning'); return redirect('/dashboard')

    # [SOLID] Gọi Logic tính toán từ Service
    status, msg = TimekeepingService.calculate_checkout_status(now, user.shift, att.status)
    
    att.check_out_time = now
    att.status = status
    db.session.commit()
    flash(msg, 'success')
    return redirect('/dashboard')

# ==================================================
# 5. API THỐNG KÊ (Biểu đồ)
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
        bar_l, bar_d = [], []
        temp = {d[0]: d[1] for d in daily}
        for i in range(7):
            d = week_ago + timedelta(days=i)
            bar_l.append(d.strftime('%d/%m'))
            bar_d.append(temp.get(d, 0))
            
        return jsonify({'success': True, 'pie': pie, 'bar': {'labels': bar_l, 'data': bar_d}})
    except Exception as e: return jsonify({'success': False, 'message': str(e)}), 500

# ==================================================
# 6. FACE ID & QR CODE (Có fix lỗi ảnh)
# ==================================================
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
            
        # [SOLID] Gọi Service
        status, _, _ = TimekeepingService.calculate_checkin_status(now, user.shift)
        status_class = 'success' if 'Đúng' in status else 'danger'
        
        db.session.add(Attendance(user_id=user.user_id, work_date=now.date(), check_in_time=now, status=status, notes="QR Code"))
        db.session.commit()
        return jsonify({'success': True, 'message': 'Thành công', 'user': {'full_name': user.full_name}, 'status': status, 'status_class': status_class, 'shift_name': user.shift.shift_name, 'time': now.strftime('%H:%M')})
    except: return jsonify({'success': False, 'message': 'Lỗi QR'}), 500

@app.route('/api/face-checkin', methods=['POST'])
def api_face_checkin():
    try:
        data = request.get_json()
        img_bytes = base64.b64decode(data['image'].split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # --- FIX LỖI ẢNH FACE ID ---
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img is None: return jsonify({'success': False, 'message': 'Ảnh lỗi'})
        
        if len(img.shape) == 3 and img.shape[2] == 4: img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif len(img.shape) == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        # ---------------------------
        
        boxes = face_recognition.face_locations(rgb)
        if not boxes: return jsonify({'success': False, 'message': 'Đang tìm mặt...'})
        
        unknown_enc = face_recognition.face_encodings(rgb, boxes)[0]
        users = User.query.filter(User.face_encoding != None).all()
        found = None
        for u in users:
            try:
                known = np.array(json.loads(u.face_encoding))
                if face_recognition.compare_faces([known], unknown_enc, tolerance=0.5)[0]: found = u; break
            except: continue
        
        if not found: return jsonify({'success': False, 'message': 'Không nhận diện được'})
        
        now = datetime.now()
        if Attendance.query.filter_by(user_id=found.user_id, work_date=now.date()).first():
            return jsonify({'success': False, 'message': f'{found.full_name} đã chấm công!'})
            
        # [SOLID] Gọi Service
        status, _, _ = TimekeepingService.calculate_checkin_status(now, found.shift)
        status_class = 'success' if 'Đúng' in status else 'danger'

        db.session.add(Attendance(user_id=found.user_id, work_date=now.date(), check_in_time=now, status=status, notes="FaceID"))
        db.session.commit()
        return jsonify({'success': True, 'message': f'Xin chào {found.full_name}', 'status': status, 'status_class': status_class, 'time': now.strftime('%H:%M')})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

@app.route('/register-face', methods=['GET', 'POST'])
@login_required
def register_face():
    if request.method == 'GET': return render_template('face_register.html')
    try:
        data = request.get_json()
        img_bytes = base64.b64decode(data['image'].split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # --- FIX LỖI ẢNH FACE ID ---
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if len(img.shape) == 3 and img.shape[2] == 4: img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif len(img.shape) == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        # ---------------------------
        
        boxes = face_recognition.face_locations(rgb)
        if not boxes: return jsonify({'success': False, 'message': 'Không thấy mặt'})
        
        enc = face_recognition.face_encodings(rgb, boxes)[0]
        user = User.query.get(session['user_id'])
        user.face_encoding = json.dumps(enc.tolist())
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đăng ký thành công'})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

# ==================================================
# 7. ROUTE PHỤ TRỢ (QR View, Admin...)
# ==================================================
@app.route('/my-qr')
@login_required
def my_qr():
    return render_template('my_qr.html', user=User.query.get(session['user_id']), qr_data_json=json.dumps({'user_id': session['user_id']}))

@app.route('/generate-qr')
@login_required
def generate_qr():
    img = qrcode.make(json.dumps({'user_id': session['user_id'], 'ts': str(datetime.now())}))
    buf = io.BytesIO(); img.save(buf); buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/scan')
def scan(): return render_template('scan_qr.html')

@app.route('/face-checkin')
def face_checkin_page(): return render_template('face_checkin.html')

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
        if User.query.filter_by(username=request.form['username']).first(): flash('Username tồn tại!', 'danger')
        else:
            u = User(full_name=request.form['fullName'], username=request.form['username'], password=request.form['password'], dept_id=request.form['department'], shift_id=request.form['shift'])
            db.session.add(u); db.session.commit(); flash('Thêm thành công', 'success'); return redirect('/admin/add_user')
    return render_template('admin/add_employee.html', departments=Department.query.all(), shifts=Shift.query.all())

@app.route('/admin/user/delete/<int:id>', methods=['POST'])
@admin_required
def delete_user(id):
    u = User.query.get(id)
    if u.role != 'admin': Attendance.query.filter_by(user_id=id).delete(); db.session.delete(u); db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/export_attendance')
@admin_required
def export_attendance():
    try:
        q = db.session.query(Attendance.work_date, User.full_name, Department.dept_name, Attendance.check_in_time, Attendance.check_out_time, Attendance.status, Attendance.notes).join(User).outerjoin(Department).all()
        df = pd.DataFrame(q, columns=['Ngày', 'Tên', 'Phòng', 'Vào', 'Ra', 'Trạng thái', 'Ghi chú'])
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
        out.seek(0)
        return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="BaoCao.xlsx")
    except Exception as e: return redirect('/dashboard')

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)