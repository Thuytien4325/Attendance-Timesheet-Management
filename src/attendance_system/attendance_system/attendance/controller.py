from __future__ import annotations

import io
import csv
import qrcode
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify, send_file
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

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

    @app.route("/api/checkin/qr", methods=["POST"], endpoint="api_checkin_qr")
    @login_required
    def api_checkin_qr():
        """API endpoint for QR code check-in/checkout - auto-detect based on current status"""
        try:
            data = request.get_json()
            qr_code = data.get("qr_code", "").strip()
            
            if not qr_code:
                return jsonify({
                    "success": False,
                    "message": "Mã QR không được để trống"
                }), 400
            
            user_id = int(session["user_id"])
            today = date.today()
            
            # Check if user has already checked in today
            attendance_record = container.attendance_service.get_today_record(user_id, today)
            
            if attendance_record and attendance_record.check_in_time and not attendance_record.check_out_time:
                # User has checked in but not checked out -> this is checkout
                try:
                    container.attendance_service.check_out(user_id)
                    return jsonify({
                        "success": True,
                        "action": "✓ Chấm công tan ca",
                        "message": "Chấm công tan ca bằng QR thành công!"
                    }), 200
                except ValidationError as e:
                    return jsonify({
                        "success": False,
                        "message": str(e)
                    }), 400
            else:
                # User hasn't checked in or already checked out -> this is check-in
                try:
                    container.attendance_service.check_in(user_id)
                    return jsonify({
                        "success": True,
                        "action": "✓ Chấm công vào ca",
                        "message": "Chấm công vào ca bằng QR thành công!"
                    }), 200
                except ValidationError as e:
                    return jsonify({
                        "success": False,
                        "message": str(e)
                    }), 400
            
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Lỗi hệ thống khi chấm công"
            }), 500

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

    # ===== QR CODE ENDPOINTS =====

    @app.route("/admin/qr/view", endpoint="admin_qr_view")
    @admin_required
    def admin_qr_view():
        """Admin page to view and print company QR code"""
        return render_template("admin/qr_view.html", active_page="admin_qr")

    @app.route("/admin/qr/image", endpoint="admin_qr_image")
    @admin_required
    def admin_qr_image():
        """Generate and return company QR code image"""
        try:
            # Use a secure token for the QR code
            # In production, you could use date-based token or database config
            token_data = app.config.get("QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(token_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to buffer
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            
            return send_file(buf, mimetype='image/png')
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/user/qr/image", endpoint="user_qr_image")
    @login_required
    def user_qr_image():
        """Generate and return user's personal QR code image for attendance check-in"""
        try:
            user_id = int(session["user_id"])
            # Generate QR code containing the office token (same token all employees use to check in)
            token_data = app.config.get("QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(token_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to buffer
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            
            return send_file(buf, mimetype='image/png')
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/qr/scan", endpoint="qr_scan_page")
    @login_required
    def qr_scan_page():
        """Page for staff to scan QR code"""
        return render_template("qr_scan.html")

    @app.route("/api/qr/checkin", methods=["POST"], endpoint="api_qr_checkin")
    @login_required
    def api_qr_checkin():
        """API endpoint to handle QR code scanning for check-in/out"""
        try:
            data = request.get_json()
            scanned_code = data.get("code", "").strip()

            if not scanned_code:
                return jsonify({
                    "success": False,
                    "message": "Mã QR không được để trống"
                }), 400

            # Verify QR code is valid
            token_data = app.config.get("QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")
            if scanned_code != token_data:
                return jsonify({
                    "success": False,
                    "message": "Mã QR không hợp lệ hoặc hết hạn!"
                }), 400

            user_id = int(session["user_id"])
            today = date.today()
            
            # Check if user has already checked in today
            attendance_record = container.attendance_service.get_today_record(user_id, today)
            
            if attendance_record and attendance_record.check_in_time and not attendance_record.check_out_time:
                # User has checked in but not checked out -> this is checkout
                try:
                    container.attendance_service.check_out(user_id)
                    return jsonify({
                        "success": True,
                        "action": "tan_ca",
                        "message": "✓ Chấm công tan ca thành công!"
                    }), 200
                except ValidationError as e:
                    return jsonify({
                        "success": False,
                        "message": str(e)
                    }), 400
            else:
                # User hasn't checked in or already checked out -> this is check-in
                try:
                    container.attendance_service.check_in(user_id)
                    return jsonify({
                        "success": True,
                        "action": "vao_ca",
                        "message": "✓ Chấm công vào ca thành công!"
                    }), 200
                except ValidationError as e:
                    return jsonify({
                        "success": False,
                        "message": str(e)
                    }), 400
            
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Lỗi hệ thống khi chấm công"
            }), 500

    @app.route("/api/qr/checkin/image", methods=["POST"], endpoint="api_qr_checkin_image")
    @login_required
    def api_qr_checkin_image():
        """API endpoint to accept an uploaded image, decode QR code, and perform check-in/out."""
        try:
            if 'image' not in request.files:
                return jsonify({"success": False, "message": "Thiếu file ảnh"}), 400

            file = request.files['image']
            img = Image.open(file.stream).convert('RGB')
            decoded = pyzbar_decode(img)

            if not decoded:
                return jsonify({"success": False, "message": "Không phát hiện mã QR trong ảnh"}), 400

            scanned_code = decoded[0].data.decode('utf-8').strip()

            # Verify QR code is valid
            token_data = app.config.get("QR_TOKEN", "OFFICE_CHECKIN_SYSTEM")
            if scanned_code != token_data:
                return jsonify({
                    "success": False,
                    "message": "Mã QR không hợp lệ hoặc hết hạn!"
                }), 400

            user_id = int(session["user_id"])
            today = date.today()

            attendance_record = container.attendance_service.get_today_record(user_id, today)

            if attendance_record and attendance_record.check_in_time and not attendance_record.check_out_time:
                try:
                    container.attendance_service.check_out(user_id)
                    return jsonify({"success": True, "action": "tan_ca", "message": "✓ Chấm công tan ca thành công!"}), 200
                except ValidationError as e:
                    return jsonify({"success": False, "message": str(e)}), 400
            else:
                try:
                    container.attendance_service.check_in(user_id)
                    return jsonify({"success": True, "action": "vao_ca", "message": "✓ Chấm công vào ca thành công!"}), 200
                except ValidationError as e:
                    return jsonify({"success": False, "message": str(e)}), 400

        except Exception as e:
            return jsonify({"success": False, "message": "Lỗi hệ thống khi chấm công"}), 500

    @app.route("/me/qr/manage", endpoint="user_qr_manage")
    @login_required
    def user_qr_manage():
        """Page for employee to manage their personal QR code"""
        user_id = int(session["user_id"])
        return render_template("me/qr_manage.html", user_id=user_id, active_page="user_qr_manage")

    @app.route("/api/user/qr/manage/image", endpoint="user_qr_manage_image")
    @login_required
    def user_qr_manage_image():
        """Generate and return user's personal QR code image based on user ID"""
        try:
            user_id = int(session["user_id"])
            
            # Generate QR code containing the user ID
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(str(user_id))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to buffer
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            
            return send_file(buf, mimetype='image/png')
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
