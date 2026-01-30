# These functions need to be added to home.py

@home_bp.route('/submit_explanation', methods=['POST'])
@login_required
def submit_explanation():
    # Xử lý logic giải trình (tạm thời redirect về dashboard)
    flash('Đã gửi giải trình thành công', 'success')
    return redirect(url_for('home.dashboard'))

@home_bp.route('/checkin')
@login_required
def checkin():
    user_id = session.get('user_id')
    today = datetime.now().date()
    now_time = datetime.now().time()

    # Kiểm tra xem hôm nay đã check-in chưa
    attendance = Attendance.query.filter_by(user_id=user_id, work_date=today).first()
    
    if attendance:
        flash('Hôm nay bạn đã Check-in rồi!', 'warning')
    else:
        # Tạo bản ghi mới
        new_att = Attendance(user_id=user_id, work_date=today, check_in_time=now_time, status='Present')
        db.session.add(new_att)
        db.session.commit()
        flash('Check-in thành công!', 'success')
    
    return redirect(url_for('home.dashboard'))

@home_bp.route('/checkout')
@login_required
def checkout():
    user_id = session.get('user_id')
    today = datetime.now().date()
    now_time = datetime.now().time()

    # Tìm bản ghi check-in hôm nay
    attendance = Attendance.query.filter_by(user_id=user_id, work_date=today).first()
    
    if attendance:
        if attendance.check_out_time:
            flash('Bạn đã Check-out trước đó rồi!', 'warning')
        else:
            attendance.check_out_time = now_time
            db.session.commit()
            flash('Check-out thành công! Hẹn gặp lại.', 'success')
    else:
        flash('Bạn chưa Check-in nên không thể Check-out!', 'danger')
    
    return redirect(url_for('home.dashboard'))
