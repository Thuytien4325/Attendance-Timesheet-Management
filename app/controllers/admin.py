# File: app/controllers/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session
from datetime import date, timedelta, datetime
import pandas as pd
import io

from app.extensions import db
from app.utils import admin_required, login_required
from app.models.user import User, Department
from app.models.schedule import Shift, EmployeeSchedule
from app.models.attendance import Attendance

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/users')
@admin_required
def admin_users():
    return render_template('admin/admin_users.html', 
                         users=User.query.order_by(User.user_id.desc()).all(), 
                         shifts=Shift.query.all())

@admin_bp.route('/admin/add_employee', methods=['GET', 'POST'])
@admin_required
def add_employee():
    if request.method == 'POST':
        try:
            full_name = request.form.get('fullName')
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role', 'staff')
            dept_id_raw = request.form.get('dept_id')
            dept_id = int(dept_id_raw) if dept_id_raw else None

            if User.query.filter_by(username=username).first():
                flash(f'Tên đăng nhập "{username}" đã tồn tại!', 'warning')
                return redirect('/admin/add_employee')

            new_user = User(full_name=full_name, username=username, password=password, dept_id=dept_id, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Đã thêm nhân viên: {full_name}', 'success')
            return redirect(url_for('admin.admin_users')) # Lưu ý: admin.admin_users
        except Exception as e:
            flash(f'Lỗi: {str(e)}', 'danger')
    
    return render_template('admin/add_employee.html', departments=Department.query.all())

# Bạn copy tiếp các hàm admin_roster, delete_user, export_attendance vào đây...


@admin_bp.route('/admin/roster', methods=['GET', 'POST'])
@admin_required
def admin_roster():
    # week offset from querystring (0 = this week, -1 previous, +1 next)
    try:
        week_offset = int(request.args.get('week', 0))
    except ValueError:
        week_offset = 0

    base = date.today() + timedelta(weeks=week_offset)
    # start of week = Monday
    start_of_week = base - timedelta(days=base.weekday())
    dates = [start_of_week + timedelta(days=i) for i in range(7)]
    today_date = date.today()

    users = User.query.order_by(User.user_id.asc()).all()
    shifts = Shift.query.order_by(Shift.shift_id.asc()).all()

    if request.method == 'POST':
        try:
            # iterate submitted fields and upsert EmployeeSchedule
            for user in users:
                for d in dates:
                    d_str = d.strftime('%Y-%m-%d')
                    field = f'schedule_{user.user_id}_{d_str}'
                    if field not in request.form:
                        continue
                    val = request.form.get(field)
                    existing = EmployeeSchedule.query.filter_by(user_id=user.user_id, work_date=d).first()

                    if val == 'OFF' or not val:
                        if existing:
                            db.session.delete(existing)
                        continue

                    try:
                        shift_id = int(val)
                    except ValueError:
                        shift_id = None

                    if existing:
                        existing.shift_id = shift_id
                    else:
                        new_sched = EmployeeSchedule(user_id=user.user_id, shift_id=shift_id, work_date=d)
                        db.session.add(new_sched)

            db.session.commit()
            flash('Lưu lịch thành công.', 'success')
            return redirect(url_for('admin.admin_roster', week=week_offset))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi lưu lịch: {str(e)}', 'danger')

    # build schedule_map: { user_id: { 'YYYY-MM-DD': shift_id } }
    schedule_map = {}
    schedules = EmployeeSchedule.query.filter(EmployeeSchedule.work_date >= dates[0], EmployeeSchedule.work_date <= dates[-1]).all()
    for s in schedules:
        uid = s.user_id
        dkey = s.work_date.strftime('%Y-%m-%d')
        schedule_map.setdefault(uid, {})[dkey] = s.shift_id

    return render_template('admin/roster.html', users=users, shifts=shifts, schedule_map=schedule_map,
                           dates=dates, week_offset=week_offset, today_date=today_date)


@admin_bp.route('/admin/approvals')
@admin_required
def admin_approvals():
    # show attendance records waiting for approval
    attendances = Attendance.query.filter_by(approval_status='Pending').join(User).order_by(Attendance.work_date.desc()).all()
    return render_template('admin/approvals.html', attendances=attendances)


@admin_bp.route('/admin/approval/<int:id>/<action>', methods=['POST'], endpoint='process_approval')
@admin_required
def process_approval(id, action):
    att = Attendance.query.get(id)
    if not att:
        flash('Không tìm thấy bản ghi chấm công.', 'danger')
        return redirect(url_for('admin.admin_approvals'))

    try:
        if action == 'approve':
            att.approval_status = 'Approved'
            flash('Đã duyệt chấm công.', 'success')
        elif action == 'reject':
            att.approval_status = 'Rejected'
            flash('Đã từ chối chấm công.', 'warning')
        else:
            flash('Hành động không hợp lệ.', 'danger')
            return redirect(url_for('admin.admin_approvals'))

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xử lý: {str(e)}', 'danger')

    return redirect(url_for('admin.admin_approvals'))


@admin_bp.route('/admin/export_excel')
@admin_required
def export_excel():
    # Lấy dữ liệu chấm công
    attendances = Attendance.query.order_by(Attendance.work_date.desc()).all()
    
    # Tạo list dữ liệu
    data = []
    for att in attendances:
        user = User.query.get(att.user_id)
        data.append({
            'Mã NV': att.user_id,
            'Họ Tên': user.full_name if user else 'Unknown',
            'Ngày': att.work_date,
            'Vào': att.check_in_time.strftime('%H:%M') if att.check_in_time else '',
            'Ra': att.check_out_time.strftime('%H:%M') if att.check_out_time else '',
            'Trạng thái': att.status,
            'Duyệt': att.approval_status
        })
    
    # Chuyển sang DataFrame
    df = pd.DataFrame(data)
    
    # Ghi vào file Excel trong bộ nhớ (không lưu ra ổ cứng)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='ChamCong')
    
    output.seek(0)
    # Trả file Excel cho client
    return send_file(output, download_name="bao_cao_cham_cong.xlsx", as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    try:
        # 1. Tìm user theo ID
        user_to_delete = User.query.get_or_404(user_id)
        
        # 2. Không cho phép tự xóa chính mình (nếu đang đăng nhập)
        if user_to_delete.user_id == session.get('user_id'):
            flash('Bạn không thể tự xóa tài khoản của chính mình!', 'danger')
            return redirect(url_for('admin.admin_users'))

        # 3. Xóa user
        db.session.delete(user_to_delete)
        db.session.commit()
        
        flash(f'Đã xóa nhân viên {user_to_delete.full_name} thành công!', 'success')
        
    except Exception as e:
        db.session.rollback()  # Hoàn tác nếu lỗi
        flash(f'Lỗi khi xóa: {str(e)}', 'danger')

    # 4. Quay lại trang danh sách
    return redirect(url_for('admin.admin_users'))