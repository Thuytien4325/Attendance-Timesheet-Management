from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import datetime
import config  # <--- Kết nối với file config bên kia

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Hàm kết nối Database (Lấy thông tin từ config)
def get_db():
    try:
        return mysql.connector.connect(**config.DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối: {err}")
        return None

@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                session['user_id'] = user['user_id']
                session['name'] = user['full_name']
                return redirect('/dashboard')
            else:
                msg = 'Sai tài khoản hoặc mật khẩu!'
        else:
            msg = 'Không kết nối được Database! Kiểm tra lại config.py'

    return render_template('login.html', msg=msg)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/')
    
    conn = get_db()
    history = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM attendance WHERE user_id=%s ORDER BY check_in_time DESC", (session['user_id'],))
        history = cursor.fetchall()
        conn.close()
    
    return render_template('dashboard.html', name=session['name'], data=history)

@app.route('/checkin', methods=['POST'])
def checkin():
    if 'user_id' in session:
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute("INSERT INTO attendance (user_id, check_in_time, status) VALUES (%s, %s, %s)", 
                        (session['user_id'], now, 'Đúng giờ'))
            conn.commit()
            conn.close()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)