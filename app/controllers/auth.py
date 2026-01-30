# File: app/controllers/auth.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect('/dashboard')
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            session['user_id'] = user.user_id
            session['name'] = user.full_name
            session['role'] = user.role
            flash('Đăng nhập thành công!', 'success')
            return redirect('/dashboard')
        flash('Sai thông tin đăng nhập!', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')