# Attendance-Timesheet-Management

Đồ án môn học xây dựng hệ thống chấm công theo **MVC + SOLID + OOP**.

## Công nghệ
- Backend: Python (Flask)
- Frontend: HTML/CSS/Bootstrap
- Database: MySQL

## Cấu trúc chính
- `src/attendance_system/attendance_system/`: kiến trúc module chi tiết (users/shifts/attendance/payroll + Strategy/Factory)
- `database/`: `schema.sql`, `seed.sql`
- `scripts/`: init/seed DB
- `templates/`, `static/`: giao diện

## Chạy dự án
1) Cài dependencies:

`pip install -r requirements.txt`

2) Tạo schema:

`python scripts/init_db.py`

3) Seed dữ liệu demo (admin/staff):

`python scripts/seed_db.py`

4) Chạy app:

`python app.py`

## Tài khoản demo
- Admin: `admin` / `admin123`
- Staff: `nguyenvana` / `staff123`
