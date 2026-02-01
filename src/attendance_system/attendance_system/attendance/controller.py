from __future__ import annotations

import io
import csv
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for

from ..core.enums import Role
from ..core.exceptions import ValidationError
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
        """Allow only Staff role.

        Staff users can access department-scoped reports and submit requests.
        They should NOT directly mutate system data (e.g., schedules) without admin approval.
        """

        @wraps(view)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") != Role.STAFF.value:
                current_user = {"full_name": session.get("name"), "role": session.get("role")}
                return render_template("403.html", current_user=current_user), 403

            return view(*args, **kwargs)

        return wrapper

    @app.route("/dashboard", endpoint="dashboard")
    @login_required
    def dashboard():
        # Recompute today's shift from schedules so UI reflects latest assignments.
        try:
            session["shift_info"] = container.auth_service.get_shift_info_for_date(
                user_id=int(session["user_id"]),
                fallback_shift_id=session.get("shift_id"),
                work_date=date.today(),
            )
        except Exception:
            # Do not block dashboard if shift computation fails.
            pass
        data = container.attendance_service.get_history_ui(int(session["user_id"]))
        return render_template("dashboard.html", name=session.get("name"), data=data, active_page="dashboard")

    @app.route("/checkin", methods=["POST"], endpoint="checkin")
    @login_required
    def checkin():
        try:
            container.attendance_service.check_in(int(session["user_id"]))
            flash("Chấm công vào ca thành công!", "success")
        except ValidationError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Lỗi hệ thống khi chấm công vào ca", "danger")
        return redirect(url_for("dashboard"))

    @app.route("/checkout", methods=["POST"], endpoint="checkout")
    @login_required
    def checkout():
        try:
            container.attendance_service.check_out(int(session["user_id"]))
            flash("Chấm công tan ca thành công!", "success")
        except ValidationError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Lỗi hệ thống khi chấm công tan ca", "danger")
        return redirect(url_for("dashboard"))

    def _parse_date(value: str) -> date:
        return datetime.strptime(value, "%Y-%m-%d").date()

    def _render_forbidden() -> tuple[str, int]:
        current_user = {"full_name": session.get("name"), "role": session.get("role")}
        return render_template("403.html", current_user=current_user), 403

    def _write_report_csv(*, data, filename: str):
        """Write report rows to CSV response.

        Shared helper used by admin/staff/user exports.
        """

        out = io.StringIO()
        writer = csv.DictWriter(
            out,
            fieldnames=[
                "work_date",
                "user_id",
                "full_name",
                "username",
                "dept_name",
                "shift_name",
                "check_in",
                "check_out",
                "status",
                "worked_hours",
                "note",
            ],
        )
        writer.writeheader()
        for row in data.rows:
            writer.writerow(row)

        csv_bytes = out.getvalue().encode("utf-8-sig")
        return app.response_class(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.route("/me/report", methods=["GET"], endpoint="me_report")
    @login_required
    def me_report():
        today = date.today()
        start_default = today.replace(day=1)

        start_s = request.args.get("start") or start_default.strftime("%Y-%m-%d")
        end_s = request.args.get("end") or today.strftime("%Y-%m-%d")

        start = _parse_date(start_s)
        end = _parse_date(end_s)

        data = container.payroll_report_service.build_attendance_report(
            start=start,
            end=end,
            user_id=int(session["user_id"]),
        )
        return render_template(
            "me/report.html",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            rows=data.rows,
            summary=data.summary,
            active_page="me_report",
        )

    @app.route("/me/report.csv", methods=["GET"], endpoint="me_report_csv")
    @login_required
    def me_report_csv():
        if session.get("role") not in {Role.STAFF.value, Role.ADMIN.value}:
            return _render_forbidden()

        start_s = request.args.get("start")
        end_s = request.args.get("end")
        if not start_s or not end_s:
            flash("Thiếu tham số start/end", "warning")
            return redirect(url_for("me_report"))

        start = _parse_date(start_s)
        end = _parse_date(end_s)

        data = container.payroll_report_service.build_attendance_report(
            start=start,
            end=end,
            user_id=int(session["user_id"]),
        )

        filename = f"my_attendance_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
        return _write_report_csv(data=data, filename=filename)

    @app.route("/staff/report", methods=["GET"], endpoint="staff_report")
    @staff_required
    def staff_report():
        """Staff view: department-scoped attendance report.

        Business rule:
        - Staff can VIEW reports but do not get admin-wide access by default.
        - We scope the report to the staff's department (dept_id in session).
        """

        today = date.today()
        start_s = request.args.get("start") or (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_s = request.args.get("end") or today.strftime("%Y-%m-%d")

        start = _parse_date(start_s)
        end = _parse_date(end_s)

        dept_id = int(session.get("dept_id") or 0) or None
        data = container.payroll_report_service.build_attendance_report(start=start, end=end, dept_id=dept_id)
        return render_template(
            "staff/report.html",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            rows=data.rows,
            summary=data.summary,
            active_page="staff_report",
        )

    @app.route("/staff/report.csv", methods=["GET"], endpoint="staff_report_csv")
    @staff_required
    def staff_report_csv():
        """Staff CSV export: department-scoped report."""

        start_s = request.args.get("start")
        end_s = request.args.get("end")
        if not start_s or not end_s:
            flash("Thiếu tham số start/end", "warning")
            return redirect(url_for("staff_report"))

        start = _parse_date(start_s)
        end = _parse_date(end_s)

        dept_id = int(session.get("dept_id") or 0) or None
        data = container.payroll_report_service.build_attendance_report(start=start, end=end, dept_id=dept_id)

        filename = f"dept_attendance_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
        return _write_report_csv(data=data, filename=filename)

    @app.route("/admin/report", methods=["GET"], endpoint="admin_report")
    @admin_required
    def admin_report():
        today = date.today()
        start_s = request.args.get("start") or (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_s = request.args.get("end") or today.strftime("%Y-%m-%d")

        start = _parse_date(start_s)
        end = _parse_date(end_s)

        data = container.payroll_report_service.build_attendance_report(start=start, end=end)
        return render_template(
            "admin/report.html",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            rows=data.rows,
            summary=data.summary,
            active_page="admin_report",
        )

    @app.route("/admin/report.csv", methods=["GET"], endpoint="admin_report_csv")
    @admin_required
    def admin_report_csv():
        start_s = request.args.get("start")
        end_s = request.args.get("end")
        if not start_s or not end_s:
            flash("Thiếu tham số start/end", "warning")
            return redirect(url_for("admin_report"))

        start = _parse_date(start_s)
        end = _parse_date(end_s)

        data = container.payroll_report_service.build_attendance_report(start=start, end=end)

        filename = f"attendance_report_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
        return _write_report_csv(data=data, filename=filename)
