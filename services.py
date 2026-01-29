from datetime import datetime, timedelta, time
from models import EmployeeSchedule, Attendance, db

# CẤU HÌNH HỆ SỐ LƯƠNG (Theo báo cáo)
OT_MULTIPLIER_NORMAL = 1.5  # Tăng ca ngày thường
OT_MULTIPLIER_HOLIDAY = 2.0 # Tăng ca ngày lễ/chủ nhật

class TimekeepingService:
    """
    Service xử lý logic chấm công nâng cao:
    - Hỗ trợ ca làm việc linh hoạt (Roster)
    - Hỗ trợ Ca qua đêm (Night Shift)
    - Tính toán tăng ca và hệ số lương
    """

    @staticmethod
    def get_today_shift(user_id, checkin_date):
        """
        Lấy ca làm việc của ngày hôm nay từ bảng lịch EmployeeSchedule
        """
        schedule = EmployeeSchedule.query.filter_by(
            user_id=user_id, 
            work_date=checkin_date
        ).first()
        
        if schedule and schedule.shift:
            return schedule.shift
        return None  # Không có lịch (OFF)

    @staticmethod
    def calculate_checkin_status(checkin_time, user):
        """
        Tính toán trạng thái khi vào ca
        """
        # 1. Tìm ca trong lịch của nhân viên
        today_shift = TimekeepingService.get_today_shift(user.user_id, checkin_time.date())
        
        if not today_shift:
            return 'Không có ca', False, 'Hôm nay bạn không có lịch làm việc (OFF)'

        # 2. Tạo mốc thời gian bắt đầu ca dựa trên ngày hiện tại
        shift_start_dt = datetime.combine(checkin_time.date(), today_shift.start_time)
        
        # Mốc thời gian tối đa cho phép đi muộn (Grace period)
        # Sử dụng thuộc tính 'late_grace_period' nếu có trong model Shift, nếu không mặc định 15 phút
        grace_minutes = getattr(today_shift, 'late_grace_period', 15)
        allowed_limit = shift_start_dt + timedelta(minutes=grace_minutes)

        if checkin_time <= allowed_limit:
            return (
                'Đúng giờ', 
                False, 
                f" Vào ca {today_shift.shift_name} thành công ({checkin_time.strftime('%H:%M')})"
            )
        else:
            late_minutes = int((checkin_time - shift_start_dt).total_seconds() / 60)
            return (
                'Đi muộn', 
                True, 
                f" Muộn {late_minutes} phút (Ca {today_shift.shift_name})"
            )

    @staticmethod
    def calculate_checkout_status(checkout_time, user, current_status):
        """
        Tính toán trạng thái khi về, hỗ trợ CA QUA ĐÊM và tính hệ số lương
        """
        # Lấy ngày làm việc gốc (có thể là hôm qua nếu là ca đêm check-out sáng nay)
        # Logic đơn giản: Lấy lịch của ngày check-out trước, nếu không có mới tính toán phức tạp
        # Ở đây ta giả định check-out cho ngày check-in được lưu trong Attendance
        
        # Tìm bản ghi check-in gần nhất chưa check-out để lấy ngày gốc
        # (Trong thực tế hàm này được gọi khi đã có attendance record, ở đây ta lấy lại lịch dựa trên ngày checkout)
        # Tuy nhiên để chính xác, ta nên truyền attendance object vào. 
        # Nhưng để giữ nguyên chữ ký hàm của bạn, ta sẽ query lại lịch.
        
        work_date = checkout_time.date()
        today_shift = TimekeepingService.get_today_shift(user.user_id, work_date)
        
        # Nếu không tìm thấy lịch hôm nay, có thể đây là ca đêm của ngày hôm qua
        if not today_shift:
            yesterday = work_date - timedelta(days=1)
            yesterday_shift = TimekeepingService.get_today_shift(user.user_id, yesterday)
            # Kiểm tra xem ca hôm qua có phải ca đêm không
            if yesterday_shift and yesterday_shift.end_time < yesterday_shift.start_time:
                today_shift = yesterday_shift
                work_date = yesterday # Reset ngày làm việc về hôm qua
            else:
                return current_status, "Lỗi: Không tìm thấy ca làm việc", 0

        # --- LOGIC XỬ LÝ CA ĐÊM (NIGHT SHIFT) ---
        shift_start = today_shift.start_time
        shift_end = today_shift.end_time
        
        is_night_shift = shift_end < shift_start
        
        # Xác định thời gian chuẩn ra về (datetime)
        shift_end_dt = datetime.combine(work_date, shift_end)
        if is_night_shift:
            shift_end_dt += timedelta(days=1) # Cộng thêm 1 ngày nếu là ca đêm
            
        # Mốc thời gian tối thiểu được phép về sớm
        early_threshold_min = getattr(today_shift, 'early_leave_threshold', 15)
        early_threshold = shift_end_dt - timedelta(minutes=early_threshold_min)
        
        overtime = 0
        status_notes = []
        msg_parts = [f"Hoàn thành ca {today_shift.shift_name}"]

        # 1. Kiểm tra về sớm
        if checkout_time < early_threshold:
            early_min = int((shift_end_dt - checkout_time).total_seconds() / 60)
            status_notes.append("Về sớm")
            msg_parts.append(f"⚠️ Về sớm {early_min} phút")
        
        # 2. Kiểm tra tăng ca (OT)
        elif checkout_time > shift_end_dt:
            ot_min = int((checkout_time - shift_end_dt).total_seconds() / 60)
            # Chỉ tính OT nếu làm thêm > 30 phút (Quy tắc chung)
            if ot_min > 30:
                overtime = ot_min
                # --- TÍNH HỆ SỐ LƯƠNG (MULTIPLIER) ---
                # 0 = Thứ 2, 6 = Chủ nhật
                if work_date.weekday() == 6: 
                    multiplier = OT_MULTIPLIER_HOLIDAY
                    status_notes.append(f"Tăng ca CN (x{multiplier})")
                    msg_parts.append(f" Tăng ca {overtime}p (x{multiplier})")
                else:
                    multiplier = OT_MULTIPLIER_NORMAL
                    status_notes.append("Tăng ca")
                    msg_parts.append(f" Tăng ca {overtime}p")

        # Quyết định trạng thái cuối cùng
        # Logic: Giữ lại trạng thái 'Đi muộn' lúc vào, nối thêm trạng thái lúc ra
        final_status = current_status
        
        if status_notes:
            # Nếu lúc vào "Đúng giờ", thì ghi đè trạng thái mới
            if final_status == "Đúng giờ":
                final_status = ", ".join(status_notes)
            else:
                # Nếu đã "Đi muộn", nối thêm (VD: Đi muộn, Về sớm)
                final_status += ", " + ", ".join(status_notes)
        
        return final_status, " | ".join(msg_parts), overtime

    @staticmethod
    def approve_attendance(attendance_id, action, comment=""):
        """
        Duyệt hoặc từ chối bản ghi chấm công
        """
        att = Attendance.query.get(attendance_id)
        if not att:
            return False, "Không tìm thấy dữ liệu chấm công"
        
        if action == 'approve':
            att.approval_status = 'Approved'
            # Nếu duyệt đơn "Đi muộn", có thể reset status về sạch sẽ hơn
            if "Đi muộn" in (att.status or ""):
                att.status = f"{att.status} (Đã duyệt)"
            att.manager_comment = comment or "Đã phê duyệt"
            
        elif action == 'reject':
            att.approval_status = 'Rejected'
            att.manager_comment = comment or "Không được phê duyệt"
        else:
            return False, "Hành động không hợp lệ"
        
        db.session.commit()
        return True, f"Đã thực hiện: {action} thành công"

    @staticmethod
    def submit_explanation(attendance_id, user_id, reason):
        """Nhân viên gửi giải trình cho ngày công"""
        att = Attendance.query.get(attendance_id)
        
        # Bảo mật: Chỉ được sửa đúng bản ghi của mình
        if not att or att.user_id != user_id:
            return False, "Dữ liệu không hợp lệ"
            
        att.notes = reason # Lưu lý do vào cột notes
        att.approval_status = 'Pending' # Chuyển trạng thái sang Chờ duyệt
        
        db.session.commit()
        return True, "Đã gửi giải trình thành công!"