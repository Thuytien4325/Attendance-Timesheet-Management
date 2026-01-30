# File: app/services/time_service.py
from datetime import datetime, time, timedelta
from app.models.schedule import EmployeeSchedule

class TimekeepingService:
    @staticmethod
    def get_today_shift(user_id, date_obj):
        # 1. Tìm trong lịch xếp ca
        sch = EmployeeSchedule.query.filter_by(user_id=user_id, work_date=date_obj).first()
        if sch and sch.shift:
            return sch.shift
        # 2. Nếu không có, return None (Controller sẽ xử lý fallback)
        return None

    @staticmethod
    def calculate_checkin_status(check_in_time, user=None):
        # Logic đơn giản hóa (Bạn có thể copy code cũ của bạn vào đây)
        # Giả sử 8h là mốc
        start_time = time(8, 0)
        limit = time(8, 15) # Cho phép trễ 15p
        
        current_time = check_in_time.time()
        if current_time > limit:
            return "Đi muộn", True, "Bạn đã đi muộn"
        return "Đúng giờ", False, "Check-in thành công"

    @staticmethod
    def calculate_checkout_status(check_out_time, user, current_status):
        # Logic đơn giản hóa
        end_time = time(17, 0)
        current_time = check_out_time.time()
        
        status = current_status
        msg = "Check-out thành công"
        ot = 0
        
        if current_time < end_time:
            status = f"{current_status} | Về sớm"
            msg = "Cảnh báo: Về sớm"
        
        return status, msg, ot