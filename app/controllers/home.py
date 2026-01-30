# File: app/controllers/home.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime, date, time
from io import BytesIO
import json
import io
import qrcode
import face_recognition
import numpy as np
import cv2
import base64

from app.extensions import db
from app.utils import login_required
from app.models.user import User
from app.models.attendance import Attendance
from app.services.time_service import TimekeepingService

home_bp = Blueprint('home', __name__)

@home_bp.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    today = date.today()
    
    # Logic ca làm việc
    schedule_info = TimekeepingService.get_today_shift(user.user_id, today)
    if schedule_info:
        today_shift = {
            'shift_name': schedule_info.shift_name,
            'start_time': schedule_info.start_time,
            'end_time': schedule_info.end_time
        }
    else:
        # Fallback
        today_shift = {'shift_name': 'Hành chính (Mặc định)', 'start_time': time(8, 0), 'end_time': time(17, 0)}

    att_today = Attendance.query.filter_by(user_id=user.user_id, work_date=today).first()
    
    query = Attendance.query
    if user.role != 'admin': query = query.filter_by(user_id=user.user_id)
    history = query.order_by(Attendance.work_date.desc(), Attendance.id.desc()).limit(50).all()

    # Xử lý data hiển thị (giữ nguyên logic cũ)
    data = []
    stats = {'total': len(history), 'on_time': 0, 'late': 0, 'early': 0}
    for row in history:
        st = row.status.lower() if row.status else ""
        css_class = 'bg-secondary'
        if 'đúng' in st: stats['on_time'] += 1; css_class = 'bg-success'
        elif 'muộn' in st: stats['late'] += 1; css_class = 'bg-danger'
        elif 'sớm' in st: stats['early'] += 1; css_class = 'bg-warning text-dark'
        
        approval_css = 'text-warning'
        if row.approval_status == 'Approved': approval_css = 'text-success'
        elif row.approval_status == 'Rejected': approval_css = 'text-danger'

        data.append({
            'id': row.id,
            'user_id': row.user_id,
            'full_name': row.user.full_name if row.user else 'Unknown',
            'date': row.work_date.strftime('%d/%m/%Y'),
            'check_in': row.check_in_time.strftime('%H:%M') if row.check_in_time else '--:--',
            'check_out': row.check_out_time.strftime('%H:%M') if row.check_out_time else '--:--',
            'status': row.status,
            'notes': row.notes,
            'approval': row.approval_status,
            'approval_css': approval_css,
            'css_class': css_class
        })

    return render_template('dashboard.html', attendance_today=att_today, stats=stats, data=data, today_shift=today_shift)

@home_bp.route('/checkin', methods=['POST'])
@login_required
def checkin():
    user = User.query.get(session['user_id'])
    now = datetime.now()
    if Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first():
        flash('Đã check-in rồi!', 'warning'); return redirect('/dashboard')
    
    status, is_late, msg = TimekeepingService.calculate_checkin_status(now, user)
    new_att = Attendance(user_id=user.user_id, work_date=now.date(), check_in_time=now, status=status, notes="Thủ công")
    db.session.add(new_att)
    db.session.commit()
    flash(msg, 'danger' if is_late else 'success')
    return redirect('/dashboard')

@home_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    user = User.query.get(session['user_id'])
    now = datetime.now()
    att = Attendance.query.filter_by(user_id=user.user_id, work_date=now.date()).first()
    if not att: flash('Chưa check-in!', 'warning'); return redirect('/dashboard')
    if att.check_out_time: flash('Đã check-out!', 'warning'); return redirect('/dashboard')

    status, msg, ot = TimekeepingService.calculate_checkout_status(now, user, att.status)
    att.check_out_time = now; att.status = status; att.overtime_minutes = ot
    db.session.commit()
    flash(msg, 'success')
    return redirect('/dashboard')

# --- API FACE CHECKIN (Logic cũ của bạn) ---
@home_bp.route('/api/face-checkin', methods=['POST'])
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
            if face_recognition.compare_faces([np.array(json.loads(u.face_encoding))], unknown, tolerance=0.5)[0]: 
                found = u; break
        
        if not found: return jsonify({'success': False, 'message': 'Không nhận diện được'})
        
        # Logic Checkin/Checkout giống cũ
        now = datetime.now(); today = now.date()
        att = Attendance.query.filter_by(user_id=found.user_id, work_date=today).first()
        
        if not att:
            status, _, _ = TimekeepingService.calculate_checkin_status(now, found)
            db.session.add(Attendance(user_id=found.user_id, work_date=today, check_in_time=now, status=status, notes="FaceID"))
            db.session.commit()
            return jsonify({'success': True, 'message': f'Xin chào {found.full_name}', 'time': now.strftime('%H:%M')})
        elif not att.check_out_time:
            status, _, _ = TimekeepingService.calculate_checkout_status(now, found, att.status)
            att.check_out_time = now; att.status = status; att.notes = (att.notes or "") + " | Face Out"
            db.session.commit()
            return jsonify({'success': True, 'message': f'Tạm biệt {found.full_name}', 'time': now.strftime('%H:%M')})
            
        return jsonify({'success': False, 'message': 'Đã chấm công rồi'})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

# --- Các route phụ khác ---
@home_bp.route('/face-checkin')
def face_checkin_page(): return render_template('face_checkin.html')

@home_bp.route('/my_qr')
@login_required
def my_qr():
    # Lấy thông tin user từ session hoặc database để hiển thị lên giao diện
    # Giả sử bạn có hàm lấy user theo ID, hoặc lấy tạm từ session
    user_info = {
        'full_name': session.get('user_name', 'Nhân viên'),
        'role': 'Nhân viên',
        'avatar': '' # Để trống để dùng default avatar
    }
    return render_template('my_qr.html', user=user_info)

@home_bp.route('/scan')
@login_required
def scan():
    return render_template('scan.html')

@home_bp.route('/generate_qr')
@login_required
def generate_qr():
    """Hàm này tạo hình ảnh QR Code từ User ID"""
    user_id = str(session.get('user_id'))
    
    # Tạo QR Code
    img = qrcode.make(user_id)
    
    # Lưu ảnh vào bộ nhớ đệm (RAM) thay vì lưu ra file ổ cứng
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    
    return send_file(buf, mimetype='image/png')

@home_bp.route('/scan-checkin', methods=['POST'])
def scan_checkin():
    """Hàm này nhận dữ liệu từ máy quét (Ajax fetch)"""
    try:
        data = request.get_json()
        qr_content = data.get('qr_data') # Đây là User ID quét được
        
        # --- LOGIC CHẤM CÔNG Ở ĐÂY ---
        # 1. Tìm nhân viên có ID = qr_content
        # 2. Kiểm tra xem hôm nay họ đã Check-in chưa
        # 3. Lưu vào database
        
        # Ví dụ phản hồi giả lập (Bạn thay bằng code DB thật của bạn):
        print(f"Đã quét được ID: {qr_content}")
        
        # Giả lập thành công
        response = {
            'success': True,
            'message': f'Đã điểm danh cho ID: {qr_content}',
            'time': datetime.now().strftime('%H:%M:%S')
        }
        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi Server: {str(e)}'})

@home_bp.route('/submit_explanation', methods=['POST'])
@login_required
def submit_explanation():
    # Xử lý logic giải trình (tạm thời redirect về dashboard)
    flash('Đã gửi giải trình thành công', 'success')