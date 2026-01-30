# File: app/utils.py
from functools import wraps
from flask import session, redirect, render_template

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