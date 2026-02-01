from __future__ import annotations

from datetime import date, datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for

from ..core.enums import Role
from ..core.exceptions import AuthorizationError, ValidationError
from ..container import Container


def register(app: Flask, container: Container) -> None:
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

    def staff_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") != Role.STAFF.value:
                current_user = {"full_name": session.get("name"), "role": session.get("role")}
                return render_template("403.html", current_user=current_user), 403
            return view(*args, **kwargs)

        return wrapper

    def _parse_date(v: str) -> date:
        return datetime.strptime(v, "%Y-%m-%d").date()

    @app.route("/requests", methods=["GET"], endpoint="my_requests")
    @login_required
    def my_requests():
        data = container.request_service.list_my_requests(user_id=int(session["user_id"]))
        return render_template(
            "requests/index.html",
            adjustments=data["adjustments"],
            leaves=data["leaves"],
            schedule_changes=data["schedule_changes"],
            active_page="my_requests",
        )

    @app.route("/requests/adjustments/new", methods=["GET", "POST"], endpoint="new_adjustment")
    @staff_required
    def new_adjustment():
        if request.method == "POST":
            try:
                work_date = _parse_date(request.form.get("work_date") or "")
                req_in = request.form.get("requested_check_in", "")
                req_out = request.form.get("requested_check_out", "")
                req_note = request.form.get("requested_note", "")

                container.request_service.create_timesheet_adjustment(
                    current_role=Role(session.get("role")),
                    user_id=int(session["user_id"]),
                    work_date=work_date,
                    requested_check_in=req_in,
                    requested_check_out=req_out,
                    requested_note=req_note,
                )
                flash("Đã gửi yêu cầu chỉnh sửa", "success")
                return redirect(url_for("my_requests"))
            except (ValidationError, AuthorizationError) as e:
                flash(str(e), "danger")
            except Exception:
                flash("Lỗi hệ thống khi gửi yêu cầu", "danger")

        return render_template("requests/new_adjustment.html", active_page="new_adjustment")

    @app.route("/requests/leaves/new", methods=["GET", "POST"], endpoint="new_leave")
    @staff_required
    def new_leave():
        if request.method == "POST":
            try:
                start_date = _parse_date(request.form.get("start_date") or "")
                end_date = _parse_date(request.form.get("end_date") or "")
                reason = request.form.get("reason", "")

                container.request_service.create_leave(
                    current_role=Role(session.get("role")),
                    user_id=int(session["user_id"]),
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                )
                flash("Đã gửi yêu cầu nghỉ phép", "success")
                return redirect(url_for("my_requests"))
            except (ValidationError, AuthorizationError) as e:
                flash(str(e), "danger")
            except Exception:
                flash("Lỗi hệ thống khi gửi yêu cầu", "danger")

        return render_template("requests/new_leave.html", active_page="new_leave")

    @app.route("/requests/schedules/new", methods=["GET", "POST"], endpoint="new_schedule_change")
    @staff_required
    def new_schedule_change():
        shifts = container.shifts_repo.list_all()

        if request.method == "POST":
            try:
                work_date = _parse_date(request.form.get("work_date") or "")
                requested_shift_id = int(request.form.get("requested_shift_id") or 0)
                requested_note = request.form.get("requested_note", "")

                container.request_service.create_schedule_change(
                    current_role=Role(session.get("role")),
                    user_id=int(session["user_id"]),
                    work_date=work_date,
                    requested_shift_id=requested_shift_id,
                    requested_note=requested_note,
                )
                flash("Đã gửi đề xuất lịch làm. Vui lòng chờ Admin duyệt.", "success")
                return redirect(url_for("my_requests"))
            except (ValidationError, AuthorizationError) as e:
                flash(str(e), "danger")
            except Exception:
                flash("Lỗi hệ thống khi gửi đề xuất lịch làm", "danger")

        return render_template(
            "requests/new_schedule_change.html",
            shifts=shifts,
            active_page="new_schedule_change",
        )

    @app.route("/admin/requests", methods=["GET"], endpoint="admin_requests")
    @admin_required
    def admin_requests():
        data = container.request_service.list_admin_pending()
        return render_template(
            "admin/requests.html",
            adjustments=data["adjustments"],
            leaves=data["leaves"],
            schedule_changes=data["schedule_changes"],
            active_page="admin_requests",
        )

    @app.route("/admin/requests/adjustments/<int:request_id>/approve", methods=["POST"], endpoint="approve_adjustment")
    @admin_required
    def approve_adjustment(request_id: int):
        try:
            container.request_service.approve_timesheet_adjustment(
                current_role=Role(session.get("role")),
                admin_user_id=int(session["user_id"]),
                request_id=int(request_id),
                admin_note=request.form.get("admin_note", ""),
            )
            flash("Đã duyệt yêu cầu", "success")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi duyệt yêu cầu", "danger")
        return redirect(url_for("admin_requests"))

    @app.route("/admin/requests/adjustments/<int:request_id>/reject", methods=["POST"], endpoint="reject_adjustment")
    @admin_required
    def reject_adjustment(request_id: int):
        try:
            container.request_service.reject_timesheet_adjustment(
                current_role=Role(session.get("role")),
                admin_user_id=int(session["user_id"]),
                request_id=int(request_id),
                admin_note=request.form.get("admin_note", ""),
            )
            flash("Đã từ chối yêu cầu", "info")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi từ chối yêu cầu", "danger")
        return redirect(url_for("admin_requests"))

    @app.route("/admin/requests/leaves/<int:request_id>/approve", methods=["POST"], endpoint="approve_leave")
    @admin_required
    def approve_leave(request_id: int):
        try:
            container.request_service.approve_leave(
                current_role=Role(session.get("role")),
                admin_user_id=int(session["user_id"]),
                request_id=int(request_id),
                admin_note=request.form.get("admin_note", ""),
            )
            flash("Đã duyệt nghỉ phép", "success")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi duyệt nghỉ phép", "danger")
        return redirect(url_for("admin_requests"))

    @app.route("/admin/requests/leaves/<int:request_id>/reject", methods=["POST"], endpoint="reject_leave")
    @admin_required
    def reject_leave(request_id: int):
        try:
            container.request_service.reject_leave(
                current_role=Role(session.get("role")),
                admin_user_id=int(session["user_id"]),
                request_id=int(request_id),
                admin_note=request.form.get("admin_note", ""),
            )
            flash("Đã từ chối nghỉ phép", "info")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi từ chối nghỉ phép", "danger")
        return redirect(url_for("admin_requests"))

    @app.route(
        "/admin/requests/schedules/<int:request_id>/approve",
        methods=["POST"],
        endpoint="approve_schedule_change",
    )
    @admin_required
    def approve_schedule_change(request_id: int):
        try:
            container.request_service.approve_schedule_change(
                current_role=Role(session.get("role")),
                admin_user_id=int(session["user_id"]),
                request_id=int(request_id),
                admin_note=request.form.get("admin_note", ""),
            )
            flash("Đã duyệt đề xuất lịch làm", "success")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi duyệt đề xuất lịch làm", "danger")
        return redirect(url_for("admin_requests"))

    @app.route(
        "/admin/requests/schedules/<int:request_id>/reject",
        methods=["POST"],
        endpoint="reject_schedule_change",
    )
    @admin_required
    def reject_schedule_change(request_id: int):
        try:
            container.request_service.reject_schedule_change(
                current_role=Role(session.get("role")),
                admin_user_id=int(session["user_id"]),
                request_id=int(request_id),
                admin_note=request.form.get("admin_note", ""),
            )
            flash("Đã từ chối đề xuất lịch làm", "info")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi từ chối đề xuất lịch làm", "danger")
        return redirect(url_for("admin_requests"))
