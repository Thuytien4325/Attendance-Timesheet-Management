from datetime import datetime, timedelta

class TimekeepingService:
    """
    Service chịu trách nhiệm tính toán logic chấm công.
    """
    
    @staticmethod
    def calculate_checkin_status(checkin_time, shift):
        if not shift:
            return 'Không xác định', False, 'Chưa xếp ca'
            
        shift_start_dt = datetime.combine(checkin_time.date(), shift.start_time)
        allowed_limit = shift_start_dt + timedelta(minutes=shift.late_grace_period)

        if checkin_time <= allowed_limit:
            return 'Đúng giờ', False, f"✅ Check-in thành công lúc {checkin_time.strftime('%H:%M')}"
        else:
            late_minutes = int((checkin_time - shift_start_dt).total_seconds() / 60)
            return 'Đi muộn', True, f"⏰ Muộn {late_minutes} phút"

    @staticmethod
    def calculate_checkout_status(checkout_time, shift, current_status):
        if not shift:
            return current_status, "Chưa xếp ca"

        shift_end_dt = datetime.combine(checkout_time.date(), shift.end_time)
        early_threshold = shift_end_dt - timedelta(minutes=shift.early_leave_threshold)

        if checkout_time < early_threshold:
            return 'Về sớm', f"⚠️ Về sớm lúc {checkout_time.strftime('%H:%M')}"
        
        final_status = current_status if current_status == 'Đi muộn' else 'Đúng giờ'
        return final_status, "✅ Hoàn thành ca làm việc"