from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import mysql.connector
from datetime import datetime, timedelta, date
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7) 

# Giả lập CSRF
app.jinja_env.globals['csrf_token'] = lambda: ''

def get_db():
    try:
        return mysql.connector.connect(**config.DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Lỗi DB: {err}")
        return None

# ==================================================
# 1. MIDDLEWARE / DECORATORS
# ==================================================
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
            return render_template('403.html', current_user={'full_name': session.get('name'), 'role': session.get('role')}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================================================
# 2. LOGIN & LOGOUT
# ==================================================
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect('/dashboard')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember_me')
        
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT users.*, shifts.shift_name, shifts.start_time, shifts.end_time 
                FROM users 
                LEFT JOIN shifts ON users.shift_id = shifts.shift_id 
                WHERE username=%s AND password=%s
            """, (username, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                session.permanent = True if remember else False
                session['user_id'] = user['user_id']
                session['name'] = user['full_name']
                session['role'] = user['role']
                session['dept_id'] = user['dept_id']
                session['shift_id'] = user['shift_id']
                
                if user['shift_name']:
                    s_time = str(user['start_time'])
                    e_time = str(user['end_time'])
                    session['shift_info'] = f"{user['shift_name']} ({s_time} - {e_time})"
                else:
                    session['shift_info'] = "Chưa xếp ca"
                
                flash('Đăng nhập thành công!', 'success')
                return redirect('/dashboard')
            else:
                flash('Sai tài khoản hoặc mật khẩu!', 'danger')
        else:
            flash('Lỗi kết nối CSDL!', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất hệ thống.', 'info')
    return redirect('/')

# ==================================================
# 3. DASHBOARD (LOGIC PHÂN QUYỀN DỮ LIỆU)
# ==================================================
@app.route('/dashboard')
@login_required 
def dashboard():
    conn = get_db()
    if not conn: return "Lỗi Database"

    cursor = conn.cursor(dictionary=True)
    
    # 1. Lấy trạng thái check-in hôm nay (Của riêng User đó để hiện nút bấm)
    cursor.execute("""
        SELECT * FROM attendance 
        WHERE user_id=%s AND work_date = CURDATE()
    """, (session['user_id'],))
    attendance_today = cursor.fetchone()

    # 2. Lấy dữ liệu bảng Lịch sử (PHẦN QUAN TRỌNG ĐỂ ADMIN THẤY HẾT)
    if session.get('role') == 'admin':
        # Nếu là ADMIN: Lấy 50 bản ghi mới nhất của TẤT CẢ mọi người
        cursor.execute("""
            SELECT a.*, u.full_name 
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            ORDER BY a.check_in_time DESC 
            LIMIT 50
        """)
    else:
        # Nếu là STAFF: Chỉ lấy của chính mình
        cursor.execute("""
            SELECT *, '' as full_name 
            FROM attendance 
            WHERE user_id=%s 
            ORDER BY check_in_time DESC 
            LIMIT 30
        """, (session['user_id'],))
        
    data = cursor.fetchall()
    
    # Format dữ liệu để hiển thị
    formatted_history = []
    stats = {'total_days': 0, 'on_time': 0, 'late': 0, 'early': 0}
    stats['total_days'] = len(data)

    for row in data:
        # Format ngày giờ
        date_str = row['check_in_time'].strftime('%d/%m/%Y')
        in_time = row['check_in_time'].strftime('%H:%M')
        out_time = row['check_out_time'].strftime('%H:%M') if row['check_out_time'] else "--:--"
        
        # Thống kê (Lưu ý: Admin sẽ thấy thống kê tổng của cty, Staff thấy của mình)
        if row['status'] == 'Đúng giờ' or row['status'] == 'on_time': stats['on_time'] += 1
        elif row['status'] == 'Đi muộn' or row['status'] == 'late': stats['late'] += 1
        elif row['status'] == 'Về sớm' or row['status'] == 'early_leave': stats['early'] += 1

        # Màu sắc badge
        status_map = {'Đúng giờ': 'bg-success', 'on_time': 'bg-success', 
                      'Đi muộn': 'bg-danger', 'late': 'bg-danger',
                      'Về sớm': 'bg-warning text-dark', 'early_leave': 'bg-warning text-dark'}
        css_class = status_map.get(row['status'], 'bg-secondary')
        
        # Dịch trạng thái sang tiếng Việt nếu cần
        status_text_map = {'on_time': 'Đúng giờ', 'late': 'Đi muộn', 'early_leave': 'Về sớm'}
        status_text = status_text_map.get(row['status'], row['status'])

        formatted_history.append({
            'full_name': row.get('full_name', ''), # Tên nhân viên (chỉ Admin có)
            'date': date_str, 
            'check_in': in_time, 
            'check_out': out_time, 
            'status': status_text, 
            'css_class': css_class
        })
    
    conn.close()
    
    return render_template('dashboard.html', 
                           attendance_today=attendance_today,
                           stats=stats,
                           data=formatted_history)

# ==================================================
# 4. CHECK-IN (LOGIC NGHIỆP VỤ)
# ==================================================
@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    conn = get_db()
    if not conn: return redirect('/dashboard')
    
    try:
        cursor = conn.cursor(dictionary=True)
        user_id = session['user_id']
        shift_id = session.get('shift_id')
        now = datetime.now()

        # B1: Kiểm tra trùng
        cursor.execute("SELECT id FROM attendance WHERE user_id = %s AND work_date = %s", (user_id, now.date()))
        if cursor.fetchone():
            flash('⚠️ Hôm nay bạn đã Check-in rồi!', 'warning')
            return redirect('/dashboard')

        # B2: Lấy Shift
        if not shift_id:
            flash('❌ Bạn chưa được xếp ca!', 'danger')
            return redirect('/dashboard')
            
        cursor.execute("SELECT start_time, late_grace_period FROM shifts WHERE shift_id = %s", (shift_id,))
        shift = cursor.fetchone()
        
        # B3: Tính toán
        shift_start_seconds = shift['start_time'].total_seconds()
        shift_start_dt = datetime.combine(now.date(), (datetime.min + timedelta(seconds=shift_start_seconds)).time())
        allowed_time = shift_start_dt + timedelta(minutes=shift['late_grace_period'])
        
        if now <= allowed_time:
            status = 'on_time'
            msg_type = 'success'
            msg = f'✅ Check-in thành công lúc {now.strftime("%H:%M")} (Đúng giờ)'
        else:
            status = 'late'
            msg_type = 'danger'
            late_minutes = int((now - shift_start_dt).total_seconds() / 60)
            msg = f'⏰ Bạn đi muộn {late_minutes} phút!'

        # B4: Lưu DB (Đã fix lỗi thiếu work_date)
        cursor.execute("""
            INSERT INTO attendance (user_id, work_date, check_in_time, status) 
            VALUES (%s, %s, %s, %s)
        """, (user_id, now.date(), now, status))
        conn.commit()
        flash(msg, msg_type)

    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'danger')
    finally:
        conn.close()
        
    return redirect('/dashboard')

# ==================================================
# 5. CHECK-OUT
# ==================================================
@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    conn = get_db()
    if not conn: return redirect('/dashboard')

    try:
        cursor = conn.cursor(dictionary=True)
        user_id = session['user_id']
        shift_id = session.get('shift_id')
        now = datetime.now()

        cursor.execute("SELECT id, status FROM attendance WHERE user_id = %s AND work_date = %s", (user_id, now.date()))
        attendance = cursor.fetchone()

        if not attendance:
            flash('⚠️ Bạn chưa Check-in!', 'warning')
            return redirect('/dashboard')
        
        # Kiểm tra check-out chưa (dựa vào check_out_time IS NULL trong query update)
        
        cursor.execute("SELECT end_time, early_leave_threshold FROM shifts WHERE shift_id = %s", (shift_id,))
        shift = cursor.fetchone()
        
        shift_end_seconds = shift['end_time'].total_seconds()
        shift_end_dt = datetime.combine(now.date(), (datetime.min + timedelta(seconds=shift_end_seconds)).time())
        early_threshold = shift_end_dt - timedelta(minutes=shift['early_leave_threshold'])
        
        final_status = attendance['status']
        msg_type = 'success'
        msg_text = 'Hoàn thành ca'

        if now < early_threshold:
            final_status = 'early_leave'
            msg_type = 'warning'
            early_minutes = int((shift_end_dt - now).total_seconds() / 60)
            msg_text = f"Về sớm {early_minutes} phút"

        cursor.execute("""
            UPDATE attendance SET check_out_time = %s, status = %s
            WHERE id = %s AND check_out_time IS NULL
        """, (now, final_status, attendance['id']))
        
        if cursor.rowcount > 0:
            conn.commit()
            flash(f'👋 Check-out thành công! {msg_text}', msg_type)
        else:
            flash('⚠️ Bạn đã Check-out rồi!', 'warning')

    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect('/dashboard')

# ==================================================
# 6. ADMIN ROUTES
# ==================================================
@app.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    conn = get_db()
    if request.method == 'POST':
        try:
            full_name = request.form['fullName']
            username = request.form['username']
            password = request.form['password']
            dept_id = request.form['department']
            shift_id = request.form['shift']
            role = 'staff'

            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Tên đăng nhập đã tồn tại!', 'danger')
            else:
                cursor.execute("INSERT INTO users (full_name, username, password, dept_id, shift_id, role) VALUES (%s, %s, %s, %s, %s, %s)", 
                               (full_name, username, password, dept_id, shift_id, role))
                conn.commit()
                flash(f'Đã thêm nhân viên {full_name}!', 'success')
            return redirect('/admin/add_user')
        except Exception as e:
            flash(f'Lỗi: {str(e)}', 'danger')

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()
    cursor.execute("SELECT * FROM shifts")
    shifts = cursor.fetchall()
    conn.close()
    return render_template('admin/add_employee.html', departments=departments, shifts=shifts)

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db()
    users = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.username, u.role, d.dept_name, s.shift_name
            FROM users u
            LEFT JOIN departments d ON u.dept_id = d.dept_id
            LEFT JOIN shifts s ON u.shift_id = s.shift_id
            ORDER BY u.user_id DESC
        """)
        users = cursor.fetchall()
        conn.close()
    return render_template('admin/admin_users.html', users=users)

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    conn = get_db()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối"})
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user: return jsonify({"success": False, "message": "Không tồn tại"})
    if user['role'] == 'admin': return jsonify({"success": False, "message": "Không thể xóa Admin"})
    
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Đã xóa thành công"})

# Xử lý lỗi 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('403.html', current_user={'full_name': 'Khách', 'role': 'unknown'}), 404

if __name__ == '__main__':
    app.run(debug=True)