# Business Rules

## Roles
- `admin`: quản trị hệ thống, quản lý nhân viên, xem/xuất báo cáo chấm công
- `staff`: nhân viên chấm công

## Attendance
- Mỗi nhân viên tối đa **1 bản ghi chấm công / ngày** (`attendance_records` unique theo `(user_id, work_date)`).
- Check-in:
  - Nếu đã có bản ghi hôm nay: báo lỗi.
  - Nếu có ca làm: so sánh giờ bắt đầu ca + `grace minutes` để xác định `ON_TIME` hay `LATE`.
- Check-out:
  - Phải check-in trước.
  - Nếu chưa đến giờ kết ca và lúc check-in là `ON_TIME` thì chuyển trạng thái `EARLY_LEAVE`.

## Reports
- Tổng giờ làm = (check_out - check_in) - break_minutes; nếu chưa check-out thì 0.
