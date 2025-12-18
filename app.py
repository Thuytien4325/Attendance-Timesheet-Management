from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import mysql.connector
from datetime import datetime, timedelta
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
# 1. MIDDLEWARE / DECORATORS (ĐÚNG YÊU CẦU)
# ==================================================

# Decorator: Bắt buộc đăng nhập (Dùng cho Dashboard, Profile...)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục!', 'warning')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

# Decorator: Bắt buộc là Admin (Dùng cho trang thêm nhân viên...)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Kiểm tra đăng nhập trước
        if 'user_id' not in session:
            return redirect('/')
        
        # 2. Kiểm tra quyền
        if session.get('role') != 'admin':
            # Truyền thông tin user vào template 403 để hiển thị
            current_user = {
                'full_name': session.get('name'),
                'role': session.get('role')
            }
            return render_template('403.html', current_user=current_user), 403
            
        return f(*args, **kwargs)
    return decorated_function

# ==================================================
# 2. ROUTE LOGIN (ĐÃ BỔ SUNG SESSION)
# ==================================================
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/dashboard')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember_me')
        
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Lấy hết thông tin user + thông tin ca làm việc
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
                
                # --- [QUAN TRỌNG] LƯU ĐỦ SESSION THEO YÊU CẦU ---
                session['user_id'] = user['user_id']
                session['name'] = user['full_name']
                session['role'] = user['role']
                session['dept_id'] = user['dept_id']   # <-- Đã thêm
                session['shift_id'] = user['shift_id'] # <-- Đã thêm
                
                # Lưu text hiển thị cho đẹp
                if user['shift_name']:
                    session['shift_info'] = f"{user['shift_name']} ({user['start_time']} - {user['end_time']})"
                else:
                    session['shift_info'] = "Chưa xếp ca"
                
                flash('Đăng nhập thành công!', 'success')
                return redirect('/dashboard')
            else:
                flash('Sai tài khoản hoặc mật khẩu!', 'danger')
        else:
            flash('Lỗi kết nối CSDL!', 'danger')

    return render_template('login.html')

# ==================================================
# 3. ROUTE LOGOUT
# ==================================================
@app.route('/logout')
def logout():
    session.clear() # Xóa sạch dữ liệu
    flash('Đã đăng xuất hệ thống.', 'info')
    return redirect('/')

# ==================================================
# 4. DASHBOARD (SỬ DỤNG DECORATOR MỚI)
# ==================================================
@app.route('/dashboard')
@login_required  # <-- Đã áp dụng Decorator kiểm tra đăng nhập
def dashboard():
    conn = get_db()
    formatted_history = []
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM attendance WHERE user_id=%s ORDER BY check_in_time DESC LIMIT 30", (session['user_id'],))
        data = cursor.fetchall()
        
        for row in data:
            date_str = row['check_in_time'].strftime('%d/%m/%Y')
            in_time = row['check_in_time'].strftime('%H:%M')
            out_time = row['check_out_time'].strftime('%H:%M') if row['check_out_time'] else "--:--"
            
            status_map = {'Đúng giờ': 'bg-success', 'Đi muộn': 'bg-danger', 'Về sớm': 'bg-warning text-dark'}
            css_class = status_map.get(row['status'], 'bg-secondary')
            
            formatted_history.append({
                'id': row['id'], 'date': date_str, 'check_in': in_time, 
                'check_out': out_time, 'status': row['status'], 'css_class': css_class
            })
        conn.close()
    
    return render_template('dashboard.html', name=session['name'], data=formatted_history)

# ==================================================
# 5. ADMIN ROUTE (ĐÃ BẢO VỆ CHẶT CHẼ)
# ==================================================
@app.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required  # <-- Chỉ Admin mới vào được, Staff sẽ bị đá sang trang 403
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

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Tên đăng nhập đã tồn tại!', 'danger')
            else:
                cursor.execute("INSERT INTO users (full_name, username, password, dept_id, shift_id, role) VALUES (%s, %s, %s, %s, %s, %s)", 
                               (full_name, username, password, dept_id, shift_id, role))
                conn.commit()
                flash(f'Đã thêm nhân viên {full_name}!', 'success')
            cursor.close()
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

# ==================================================
# 6. ROUTE CHỨC NĂNG (CHECKIN/OUT)
# ==================================================
@app.route('/checkin', methods=['POST'])
@login_required # <-- Bảo vệ route này luôn
def checkin():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        now = datetime.now()
        # Ở đây bạn có thể dùng session['shift_id'] để so sánh giờ nếu muốn tính đi muộn
        cursor.execute("INSERT INTO attendance (user_id, check_in_time, status) VALUES (%s, %s, %s)", 
                        (session['user_id'], now, 'Đúng giờ'))
        conn.commit()
        conn.close()
        flash('Check-in thành công!', 'success')
    return redirect('/dashboard')

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("UPDATE attendance SET check_out_time = %s WHERE user_id = %s AND check_out_time IS NULL ORDER BY check_in_time DESC LIMIT 1", 
                       (now, session['user_id']))
        conn.commit()
        conn.close()
        flash('Check-out thành công!', 'warning')
    return redirect('/dashboard')

# Xử lý lỗi 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('403.html', current_user={'full_name': 'Khách', 'role': 'unknown'}), 404

# ==================================================
# 6.1 ADMIN - DANH SÁCH NHÂN VIÊN
# ==================================================
@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db()
    users = []

    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                users.user_id,
                users.full_name,
                users.username,
                users.role,
                departments.dept_name,
                shifts.shift_name
            FROM users
            LEFT JOIN departments ON users.dept_id = departments.dept_id
            LEFT JOIN shifts ON users.shift_id = shifts.shift_id
            ORDER BY users.user_id DESC
        """)
        users = cursor.fetchall()
        conn.close()

    return render_template('admin/admin_users.html', users=users)

# ==================================================
# 6.2 ADMIN - XÓA NHÂN VIÊN (JS FETCH)
# ==================================================
@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Lỗi kết nối CSDL"})

    cursor = conn.cursor(dictionary=True)

    # Không cho xóa admin
    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"success": False, "message": "Nhân viên không tồn tại"})

    if user['role'] == 'admin':
        conn.close()
        return jsonify({"success": False, "message": "Không thể xóa tài khoản Admin"})

    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Xóa nhân viên thành công"})

if __name__ == '__main__':
    app.run(debug=True)