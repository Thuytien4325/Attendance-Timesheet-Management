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

# --- IMPORT MODULE ---
from config import Config
from extensions import db
from models import User, Shift, Department, Attendance, EmployeeSchedule
from services import TimekeepingService

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
app.jinja_env.globals['csrf_token'] = lambda: ''

# ==================================================
# 1. MIDDLEWARE (KIỂM TRA ĐĂNG NHẬP)
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
# 2. XỬ LÝ ĐĂNG NHẬP / ĐĂNG XUẤT
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
            flash('Đăng nhập thành công!', 'success'); return redirect('/dashboard')
        flash('Sai thông tin!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

# ==================================================
# 3. TRANG DASHBOARD (ĐÃ SỬA LỖI STRFTIME)
# ==================================================
@app.route('/dashboard')
@login_required 
def dashboard():
    user = User.query.get(session['user_id'])
    today = date.today()
    
    # Lấy ca làm việc (Roster)
    today_shift = TimekeepingService.get_today_shift(user.user_id, today)
    att_today = Attendance.query.filter_by(user_id=user.user_id, work_date=today).first()

    query = Attendance.query
    if user.role != 'admin': query = query.filter_by(user_id=user.user_id)
    history = query.order_by(Attendance.work_date.desc(), Attendance.id.desc()).limit(50).all()
    
    data = []
    stats = {'total': len(history), 'on_time': 0, 'late': 0, 'early': 0}
    for row in history:
        # Xử lý an toàn cho status
        st = row.status.lower() if row.status else ""
        if 'đúng' in st: stats['on_time'] += 1
        elif 'muộn' in st: stats['late'] += 1
        elif 'sớm' in st: stats['early'] += 1
        
        # Xử lý CSS class
        css_class = 'bg-secondary'
        if 'đúng' in st: css_class = 'bg-success'
        elif 'muộn' in st: css_class = 'bg-danger'
        elif 'sớm' in st: css_class = 'bg-warning text-dark'

        data.append({
            'id': row.id,
            'full_name': row.user.full_name,
            'date': row.work_date.strftime('%d/%m/%Y'),
            # FIX LỖI: Kiểm tra None trước khi format giờ
            'check_in': row.check_in_time.strftime('%H:%M') if row.check_in_time else '--:--',
            'check_out': row.check_out_time.strftime('%H:%M') if row.check_out_time else '--:--',
            'status': row.status,
            'notes': row.notes,
            'approval': row.approval_status,
            'approval_css': 'text-warning' if row.approval_status == 'Pending' else ('text-success' if row.approval_status == 'Approved' else 'text-danger'),
            'css_class': css_class
        })

    return render_template('dashboard.html', attendance_today=att_today, stats=stats, data=data, today_shift=today_shift)

# ==================================================
# 4. CHỨC NĂNG CHẤM CÔNG (THỦ CÔNG, GIẢI TRÌNH)
# ==================================================
@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    user = User.query.get(session['user_id'])
    now = datetime.now()
    
    if Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first():
        flash('Đã check-in rồi!', 'warning'); return redirect('/dashboard')
    
    # Tính toán theo Roster
    status, is_late, msg = TimekeepingService.calculate_checkin_status(now, user)
    
    if status == 'Không có ca':
        flash(msg, 'warning'); return redirect('/dashboard')

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

    status, msg, ot = TimekeepingService.calculate_checkout_status(now, user, att.status)
    
    att.check_out_time = now
    att.status = status
    att.overtime_minutes = ot
    db.session.commit()
    flash(msg, 'success')
    return redirect('/dashboard')

@app.route('/submit_explanation', methods=['POST'])
@login_required
def submit_explanation():
    user_id = session['user_id']
    reason = request.form.get('reason')
    target_date_str = request.form.get('target_date') 
    att_id = request.form.get('attendance_id')

    if att_id: 
        success, msg = TimekeepingService.submit_explanation(att_id, user_id, reason)
    elif target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            att = Attendance.query.filter_by(user_id=user_id, work_date=target_date).first()
            if att:
                att.notes = reason; att.approval_status = 'Pending'
            else:
                db.session.add(Attendance(user_id=user_id, work_date=target_date, status='Vắng (Có phép)', notes=reason, approval_status='Pending'))
            db.session.commit(); success, msg = True, "Đã gửi đơn!"
        except Exception as e: success, msg = False, str(e)
    else: success, msg = False, "Thiếu dữ liệu"

    flash(msg, 'success' if success else 'danger'); return redirect('/dashboard')

# ==================================================
# 5. QUẢN TRỊ VIÊN (ADMIN) - ĐÃ SỬA LỖI EXPORT
# ==================================================
@app.route('/admin/roster', methods=['GET', 'POST'])
@admin_required
def admin_roster():
    week_offset = int(request.args.get('week', 0))
    today = date.today() + timedelta(weeks=week_offset)
    start_of_week = today - timedelta(days=today.weekday())
    dates = [start_of_week + timedelta(days=i) for i in range(7)]
    
    if request.method == 'POST':
        for key, shift_id in request.form.items():
            if key.startswith("schedule_"):
                parts = key.split('_')
                uid, d_str = int(parts[1]), parts[2]
                w_date = datetime.strptime(d_str, '%Y-%m-%d').date()
                sch = EmployeeSchedule.query.filter_by(user_id=uid, work_date=w_date).first()
                sid = int(shift_id) if (shift_id and shift_id != 'OFF') else None
                if not sch and sid: db.session.add(EmployeeSchedule(user_id=uid, work_date=w_date, shift_id=sid))
                elif sch: sch.shift_id = sid
        db.session.commit(); flash("Đã lưu lịch!", "success"); return redirect(url_for('admin_roster', week=week_offset))

    users = User.query.filter(User.role != 'admin').all()
    shifts = Shift.query.all()
    schedules = EmployeeSchedule.query.filter(EmployeeSchedule.work_date >= dates[0], EmployeeSchedule.work_date <= dates[6]).all()
    
    sch_map = {}
    for s in schedules:
        if s.user_id not in sch_map: sch_map[s.user_id] = {}
        sch_map[s.user_id][str(s.work_date)] = s.shift_id

    return render_template('admin/roster.html', users=users, shifts=shifts, dates=dates, schedule_map=sch_map, week_offset=week_offset, today_date=date.today())

@app.route('/admin/users')
@admin_required
def admin_users():
    return render_template('admin/admin_users.html', users=User.query.order_by(User.user_id.desc()).all(), shifts=Shift.query.all())

@app.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        u = User(full_name=request.form['fullName'], username=request.form['username'], password=request.form['password'], dept_id=request.form['department'])
        db.session.add(u); db.session.commit(); flash('Thêm thành công', 'success'); return redirect('/admin/users')
    return render_template('admin/add_employee.html', departments=Department.query.all())

@app.route('/admin/user/delete/<int:id>', methods=['POST'])
@admin_required
def delete_user(id):
    if User.query.get(id).role != 'admin':
        Attendance.query.filter_by(user_id=id).delete()
        EmployeeSchedule.query.filter_by(user_id=id).delete()
        db.session.delete(User.query.get(id)); db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/approvals')
@admin_required
def admin_approvals():
    return render_template('admin/approvals.html', attendances=Attendance.query.filter_by(approval_status='Pending').all())

@app.route('/admin/approve/<int:id>/<string:action>', methods=['POST'])
@admin_required
def process_approval(id, action):
    TimekeepingService.approve_attendance(id, action)
    return redirect(url_for('admin_approvals'))

@app.route('/admin/export_attendance')
@admin_required
def export_attendance():
    # --- ĐÃ SỬA LỖI INVALID REQUEST: THÊM select_from(Attendance) ---
    q = db.session.query(
        Attendance.work_date, 
        User.full_name, 
        Department.dept_name, 
        Attendance.check_in_time, 
        Attendance.check_out_time, 
        Attendance.status, 
        Attendance.approval_status
    ).select_from(Attendance).join(User).outerjoin(Department).all()
    
    # Xử lý format ngày giờ để xuất Excel đẹp hơn
    data_list = []
    for item in q:
        data_list.append({
            'Ngày': item.work_date,
            'Họ Tên': item.full_name,
            'Phòng': item.dept_name,
            'Vào': item.check_in_time.strftime('%H:%M') if item.check_in_time else '',
            'Ra': item.check_out_time.strftime('%H:%M') if item.check_out_time else '',
            'Trạng thái': item.status,
            'Duyệt': item.approval_status
        })

    df = pd.DataFrame(data_list)
    out = io.BytesIO(); 
    with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    out.seek(0)
    return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="BaoCao.xlsx")

# ==================================================
# 6. FACE ID & QR & API (UTILITIES)
# ==================================================
@app.route('/scan-checkin', methods=['POST'])
def scan_checkin():
    try:
        data = request.get_json(); info = json.loads(data.get('qr_data', '{}'))
        user = User.query.get(info.get('user_id'))
        if not user: return jsonify({'success': False, 'message': 'Không tìm thấy NV'}), 404
        
        now = datetime.now(); today = now.date()
        att = Attendance.query.filter_by(user_id=user.user_id, work_date=today).first()
        
        if not att: # Check-in
            status, _, msg = TimekeepingService.calculate_checkin_status(now, user)
            if status == 'Không có ca': return jsonify({'success': False, 'message': msg}), 400
            db.session.add(Attendance(user_id=user.user_id, work_date=today, check_in_time=now, status=status, notes="QR Check-in"))
            db.session.commit()
            return jsonify({'success': True, 'message': f'Xin chào {user.full_name}', 'status': status, 'time': now.strftime('%H:%M')})
        elif not att.check_out_time: # Check-out
            status, msg, ot = TimekeepingService.calculate_checkout_status(now, user, att.status)
            att.check_out_time = now; att.status = status; att.overtime_minutes = ot; att.notes = (att.notes or "") + " | QR Out"
            db.session.commit()
            return jsonify({'success': True, 'message': f'Tạm biệt {user.full_name}', 'status': status, 'time': now.strftime('%H:%M')})
        else: return jsonify({'success': False, 'message': 'Đã hoàn thành ca'}), 400
    except: return jsonify({'success': False, 'message': 'Lỗi QR'}), 500

@app.route('/api/face-checkin', methods=['POST'])
def api_face_checkin():
    try:
        data = request.get_json()
        nparr = np.frombuffer(base64.b64decode(data['image'].split(',')[1]), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        
        if len(img.shape) == 3 and img.shape[2] == 4: img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif len(img.shape) == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB); rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        
        boxes = face_recognition.face_locations(rgb)
        if not boxes: return jsonify({'success': False, 'message': 'Không thấy mặt'})
        
        unknown = face_recognition.face_encodings(rgb, boxes)[0]
        found = None
        for u in User.query.filter(User.face_encoding != None).all():
            if face_recognition.compare_faces([np.array(json.loads(u.face_encoding))], unknown, tolerance=0.5)[0]: found = u; break
        
        if not found: return jsonify({'success': False, 'message': 'Không nhận diện được'})
        
        now = datetime.now(); today = now.date()
        att = Attendance.query.filter_by(user_id=found.user_id, work_date=today).first()
        
        if not att:
            status, _, msg = TimekeepingService.calculate_checkin_status(now, found)
            if status == 'Không có ca': return jsonify({'success': False, 'message': msg})
            db.session.add(Attendance(user_id=found.user_id, work_date=today, check_in_time=now, status=status, notes="FaceID"))
            db.session.commit()
            return jsonify({'success': True, 'message': f'Xin chào {found.full_name}', 'status': status, 'time': now.strftime('%H:%M')})
        elif not att.check_out_time:
            status, msg, ot = TimekeepingService.calculate_checkout_status(now, found, att.status)
            att.check_out_time = now; att.status = status; att.overtime_minutes = ot; att.notes = (att.notes or "") + " | Face Out"
            db.session.commit()
            return jsonify({'success': True, 'message': f'Tạm biệt {found.full_name}', 'status': status, 'time': now.strftime('%H:%M')})
        return jsonify({'success': False, 'message': 'Đã chấm công rồi'})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

@app.route('/register-face', methods=['GET', 'POST'])
@login_required
def register_face():
    if request.method == 'GET': return render_template('face_register.html')
    try:
        data = request.get_json()
        nparr = np.frombuffer(base64.b64decode(data['image'].split(',')[1]), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        
        if len(img.shape) == 3 and img.shape[2] == 4: img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif len(img.shape) == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB); rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        
        boxes = face_recognition.face_locations(rgb)
        if boxes:
            enc = face_recognition.face_encodings(rgb, boxes)[0]
            u = User.query.get(session['user_id'])
            u.face_encoding = json.dumps(enc.tolist())
            db.session.commit()
            return jsonify({'success': True, 'message': 'Đã lưu khuôn mặt'})
        return jsonify({'success': False, 'message': 'Không tìm thấy mặt'})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

@app.route('/my-qr')
@login_required
def my_qr():
    return render_template('my_qr.html', user=User.query.get(session['user_id']), qr_data_json=json.dumps({'user_id': session['user_id']}))

@app.route('/generate-qr')
@login_required
def generate_qr():
    img = qrcode.make(json.dumps({'user_id': session['user_id']}))
    buf = io.BytesIO(); img.save(buf); buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/scan')
def scan(): return render_template('scan_qr.html')

@app.route('/face-checkin')
def face_checkin_page(): return render_template('face_checkin.html')

@app.route('/api/stats')
@login_required
def api_stats():
    today = date.today()
    counts = db.session.query(Attendance.status, func.count(Attendance.id)).filter(Attendance.work_date == today).group_by(Attendance.status).all()
    pie = {'on_time': 0, 'late': 0, 'early': 0}
    for s, c in counts:
        if 'đúng' in s.lower(): pie['on_time'] += c
        elif 'muộn' in s.lower(): pie['late'] += c
        elif 'sớm' in s.lower(): pie['early'] += c
    
    week_ago = today - timedelta(days=6)
    daily = db.session.query(Attendance.work_date, func.count(Attendance.id)).filter(Attendance.work_date >= week_ago).group_by(Attendance.work_date).all()
    l, d = [], []
    temp = {item[0]: item[1] for item in daily}
    for i in range(7):
        day = week_ago + timedelta(days=i)
        l.append(day.strftime('%d/%m')); d.append(temp.get(day, 0))
    return jsonify({'success': True, 'pie': pie, 'bar': {'labels': l, 'data': d}})

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)