from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
import traceback

from flask import Flask, flash, redirect, render_template, request, session, url_for

from ..core.enums import Role
from ..core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from ..container import Container


def register(app: Flask, container: Container) -> None:
    app.jinja_env.globals["csrf_token"] = lambda: ""

    def login_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Vui lòng đăng nhập để tiếp tục!", "warning")
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapper

    def admin_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") != Role.ADMIN.value:
                current_user = {"full_name": session.get("name"), "role": session.get("role")}
                return render_template("403.html", current_user=current_user), 403

            return view(*args, **kwargs)

        return wrapper

    @app.route("/", methods=["GET", "POST"], endpoint="login")
    def login():
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            remember = request.form.get("remember_me")

            try:
                s_user = container.auth_service.authenticate(username, password)

                session.permanent = bool(remember)
                app.permanent_session_lifetime = timedelta(days=7)

                session["user_id"] = s_user.user_id
                session["name"] = s_user.full_name
                session["role"] = s_user.role.value
                session["dept_id"] = s_user.dept_id
                session["shift_id"] = s_user.shift_id
                session["shift_info"] = s_user.shift_info

                flash("Đăng nhập thành công!", "success")
                return redirect(url_for("dashboard"))
            except AuthenticationError as e:
                flash(str(e), "danger")
            except Exception as e:
                traceback.print_exc()
                if bool(app.config.get("DEBUG", False)):
                    flash(f"Lỗi hệ thống khi đăng nhập: {e}", "danger")
                else:
                    flash("Lỗi hệ thống khi đăng nhập", "danger")

        return render_template("login.html")

    @app.route("/logout", endpoint="logout")
    def logout():
        session.clear()
        flash("Đã đăng xuất hệ thống.", "info")
        return redirect(url_for("login"))

    @app.route("/admin/users", endpoint="admin_users")
    @admin_required
    def admin_users():
        users = container.user_service.list_admin_view()
        return render_template("admin/admin_users.html", users=users, active_page="admin_users")

    @app.route("/admin/users/add", methods=["GET", "POST"], endpoint="add_user")
    @admin_required
    def add_user():
        if request.method == "POST":
            try:
                full_name = request.form.get("fullName", "")
                username = request.form.get("username", "")
                password = request.form.get("password", "")
                role_s = request.form.get("role", "user")
                dept_id = int(request.form.get("department") or 0)
                shift_id = int(request.form.get("shift") or 0)

                try:
                    role = Role(role_s)
                except ValueError:
                    raise ValidationError("Loại tài khoản không hợp lệ")

                container.user_service.create_account(
                    full_name=full_name,
                    username=username,
                    password=password,
                    role=role,
                    dept_id=dept_id,
                    shift_id=shift_id,
                )

                flash("Thêm nhân viên thành công!", "success")
                return redirect(url_for("admin_users"))
            except (ValidationError, AuthorizationError) as e:
                flash(str(e), "danger")
            except Exception:
                flash("Lỗi hệ thống khi thêm nhân viên", "danger")

        departments = container.departments_repo.list_all()
        shifts = container.shifts_repo.list_all()
        return render_template(
            "admin/add_employee.html",
            departments=departments,
            shifts=shifts,
            active_page="add_user",
        )

    @app.route("/admin/users/delete/<int:user_id>", methods=["POST"], endpoint="delete_user")
    @admin_required
    def delete_user(user_id: int):
        try:
            container.user_service.delete_user(current_role=Role(session.get("role")), user_id=user_id)
            flash("Đã xóa nhân viên.", "success")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi xóa nhân viên", "danger")

        return redirect(url_for("admin_users"))
