# File: app/__init__.py
from flask import Flask
from config import Config
from app.extensions import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Khởi tạo DB
    db.init_app(app)

    # Mock CSRF
    app.jinja_env.globals['csrf_token'] = lambda: ''

    with app.app_context():
        # Import Models để SQLAlchemy tạo bảng
        from app.models.user import User, Department
        from app.models.attendance import Attendance
        from app.models.schedule import Shift, EmployeeSchedule

        # Import Controllers (Blueprints)
        from app.controllers.auth import auth_bp
        from app.controllers.home import home_bp
        from app.controllers.admin import admin_bp

        # Đăng ký Blueprints
        app.register_blueprint(auth_bp)
        app.register_blueprint(home_bp)
        app.register_blueprint(admin_bp)

        # Tạo bảng
        db.create_all()

    return app