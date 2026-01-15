from datetime import datetime, timedelta
from models import EmployeeSchedule, Attendance, db

class TimekeepingService:
    """
    Service xử lý logic chấm công dựa trên lịch làm việc linh hoạt (Roster)
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
        allowed_limit = shift_start_dt + timedelta(minutes=today_shift.late_grace_period)

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
        Tính toán trạng thái khi về và số phút tăng ca (OT)
        """
        today_shift = TimekeepingService.get_today_shift(user.user_id, checkout_time.date())
        
        if not today_shift:
            return current_status, "Lỗi: Không tìm thấy ca làm việc", 0

        # Mốc thời gian kết thúc ca
        shift_end_dt = datetime.combine(checkout_time.date(), today_shift.end_time)
        # Mốc thời gian tối thiểu được phép về sớm không bị phạt
        early_threshold = shift_end_dt - timedelta(minutes=today_shift.early_leave_threshold)
        
        overtime = 0
        status = current_status
        msg = f" Hoàn thành ca {today_shift.shift_name}"

        # 1. Kiểm tra về sớm
        if checkout_time < early_threshold:
            status = 'Về sớm'
            msg = f"⚠️ Về sớm lúc {checkout_time.strftime('%H:%M')}"
        
        # 2. Kiểm tra tăng ca (OT)
        elif checkout_time > shift_end_dt:
            overtime = int((checkout_time - shift_end_dt).total_seconds() / 60)
            msg = f" Hoàn thành ca (Tăng ca {overtime} phút)"

        # Quyết định trạng thái cuối cùng (Ưu tiên giữ lỗi 'Về sớm' hoặc 'Đi muộn')
        final_status = (
            'Về sớm' if status == 'Về sớm' 
            else ('Đi muộn' if current_status == 'Đi muộn' else 'Đúng giờ')
        )
        
        return final_status, msg, overtime

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
        from models import Attendance
        from extensions import db
        
        att = Attendance.query.get(attendance_id)
        
        # Bảo mật: Chỉ được sửa đúng bản ghi của mình
        if not att or att.user_id != user_id:
            return False, "Dữ liệu không hợp lệ"
            
        att.notes = reason # Lưu lý do vào cột notes
        att.approval_status = 'Pending' # Chuyển trạng thái sang Chờ duyệt
        
        db.session.commit()
        return True, "Đã gửi giải trình thành công!"