from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import datetime
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# --- GIẢI PHÁP THAY THẾ CSRF (Để không bị lỗi template mà không cần cài thêm thư viện) ---
app.jinja_env.globals['csrf_token'] = lambda: ''

# Hàm kết nối DB
def get_db():
    try:
        return mysql.connector.connect(**config.DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Lỗi DB: {err}")
        return None

# === 1. ĐĂNG NHẬP (Cập nhật lấy thông tin Ca làm việc) ===
@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # JOIN bảng shifts để lấy tên ca và giờ làm việc
            cursor.execute("""
                SELECT users.*, shifts.shift_name, shifts.start_time, shifts.end_time 
                FROM users 
                LEFT JOIN shifts ON users.shift_id = shifts.shift_id 
                WHERE username=%s AND password=%s
            """, (username, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                session['user_id'] = user['user_id']
                session['name'] = user['full_name']
                session['role'] = user['role']
                
                # Lưu thông tin ca vào session để hiển thị ở Navbar
                if user['shift_name']:
                    session['shift_info'] = f"{user['shift_name']} ({user['start_time']} - {user['end_time']})"
                else:
                    session['shift_info'] = "Chưa xếp ca"
                
                return redirect('/dashboard')
            else:
                msg = 'Sai tài khoản hoặc mật khẩu!'
        else:
            msg = 'Không kết nối được Database!'

    return render_template('login.html', msg=msg)

# === 2. DASHBOARD (Cập nhật Logic Badge màu và Format ngày giờ) ===
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/')
    
    conn = get_db()
    formatted_history = []
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM attendance WHERE user_id=%s ORDER BY check_in_time DESC", (session['user_id'],))
        data = cursor.fetchall()
        
        for row in data:
            # Format Ngày: dd/mm/yyyy
            date_str = row['check_in_time'].strftime('%d/%m/%Y')
            
            # Format Giờ vào: HH:MM
            in_time = row['check_in_time'].strftime('%H:%M')
            
            # Format Giờ ra
            if row['check_out_time']:
                out_time = row['check_out_time'].strftime('%H:%M')
            else:
                out_time = "--:--"
            
            # Logic Badge màu sắc
            status = row['status']
            css_class = 'bg-secondary' # Mặc định
            
            if status == 'Đúng giờ':
                css_class = 'bg-success' # Xanh
            elif status == 'Đi muộn':
                css_class = 'bg-danger'  # Đỏ
            elif status == 'Về sớm':
                css_class = 'bg-warning text-dark' # Vàng
            
            formatted_history.append({
                'id': row['id'],
                'date': date_str,
                'check_in': in_time,
                'check_out': out_time,
                'status': status,
                'css_class': css_class
            })
        conn.close()
    
    return render_template('dashboard.html', name=session['name'], data=formatted_history)

# === 3. CHECK-IN & CHECK-OUT ===
@app.route('/checkin', methods=['POST'])
def checkin():
    if 'user_id' in session:
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            now = datetime.now()
            # Logic giả định: Vào là 'Đúng giờ' (Thực tế cần so sánh với bảng shifts)
            cursor.execute("INSERT INTO attendance (user_id, check_in_time, status) VALUES (%s, %s, %s)", 
                           (session['user_id'], now, 'Đúng giờ'))
            conn.commit()
            conn.close()
            flash('Check-in thành công!', 'success')
    return redirect('/dashboard')

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' in session:
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            now = datetime.now()
            # Update check_out_time cho bản ghi mới nhất chưa có giờ ra
            cursor.execute("""
                UPDATE attendance SET check_out_time = %s 
                WHERE user_id = %s AND check_out_time IS NULL 
                ORDER BY check_in_time DESC LIMIT 1
            """, (now, session['user_id']))
            conn.commit()
            conn.close()
            flash('Check-out thành công!', 'warning')
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# === 4. ADMIN THÊM NHÂN VIÊN (Cập nhật Check trùng User) ===
@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/dashboard')

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
            
            # Kiểm tra trùng username
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Tên đăng nhập đã tồn tại! Vui lòng chọn tên khác.', 'danger')
            else:
                cursor.execute("""
                    INSERT INTO users (full_name, username, password, dept_id, shift_id, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (full_name, username, password, dept_id, shift_id, role))
                conn.commit()
                flash(f'Đã thêm nhân viên {full_name}!', 'success')
            
            cursor.close()
            return redirect('/admin/add_user')

        except Exception as e:
            flash(f'Lỗi: {str(e)}', 'danger')

    # GET: Load dropdown
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()
    cursor.execute("SELECT * FROM shifts")
    shifts = cursor.fetchall()
    conn.close()
    
    return render_template('admin/add_employee.html', departments=departments, shifts=shifts)

# API Dummy để tránh lỗi JS Dashboard cũ
@app.route('/api/attendance')
def api_attendance(): return {'data': []}
@app.route('/api/stats')
def api_stats(): return {'total_days': 0, 'late': 0, 'early': 0, 'absent': 0}

if __name__ == '__main__':
    app.run(debug=True)