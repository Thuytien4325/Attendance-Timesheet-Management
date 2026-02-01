from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for

from ..core.enums import Role
from ..core.exceptions import AuthorizationError, ValidationError
from ..container import Container


def register(app: Flask, container: Container) -> None:
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

    def _parse_date(value: str) -> date:
        return datetime.strptime(value, "%Y-%m-%d").date()

    @app.route("/admin/schedules", methods=["GET", "POST"], endpoint="admin_schedules")
    @admin_required
    def admin_schedules():
        today = date.today()
        start_s = request.args.get("start") or today.strftime("%Y-%m-%d")
        end_s = request.args.get("end") or (today + timedelta(days=7)).strftime("%Y-%m-%d")
        user_id_s = request.args.get("user_id")

        if request.method == "POST":
            try:
                user_id = int(request.form.get("user_id") or 0)
                shift_id = int(request.form.get("shift_id") or 0)
                work_date = _parse_date(request.form.get("work_date") or today.strftime("%Y-%m-%d"))
                note = request.form.get("note") or None

                container.schedule_service.assign(
                    current_role=Role(session.get("role")),
                    user_id=user_id,
                    work_date=work_date,
                    shift_id=shift_id,
                    note=note,
                )
                flash("Đã phân ca thành công!", "success")
                return redirect(url_for("admin_schedules", start=start_s, end=end_s, user_id=user_id_s or ""))
            except (ValidationError, AuthorizationError) as e:
                flash(str(e), "danger")
            except Exception:
                flash("Lỗi hệ thống khi phân ca", "danger")

        start = _parse_date(start_s)
        end = _parse_date(end_s)
        user_id = int(user_id_s) if user_id_s and user_id_s.isdigit() else None

        schedules = container.schedules_repo.list_range(start=start, end=end, user_id=user_id)
        users = container.user_service.list_admin_view()
        shifts = container.shifts_repo.list_all()

        return render_template(
            "admin/schedules.html",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            schedules=schedules,
            users=users,
            shifts=shifts,
            selected_user_id=user_id,
            active_page="admin_schedules",
        )

    @app.route("/admin/schedules/delete/<int:schedule_id>", methods=["POST"], endpoint="admin_schedules_delete")
    @admin_required
    def admin_schedules_delete(schedule_id: int):
        try:
            container.schedule_service.delete(current_role=Role(session.get("role")), schedule_id=schedule_id)
            flash("Đã xóa lịch.", "success")
        except (ValidationError, AuthorizationError) as e:
            flash(str(e), "danger")
        except Exception:
            flash("Lỗi hệ thống khi xóa lịch", "danger")

        return redirect(url_for("admin_schedules"))
