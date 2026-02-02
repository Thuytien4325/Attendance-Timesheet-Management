import os

def get_settings_module() -> str:
    # Lấy giá trị môi trường từ biến APP_ENV, mặc định là 'development'
    env = os.getenv("APP_ENV", "development").lower()

    # 1. Kiểm tra môi trường Production
    if env in {"prod", "production"}:
        return "config.production"
    
    # 2. Kiểm tra môi trường Testing
    if env in {"test", "testing"}:
        return "config.testing"
    
    # 3. Mặc định trả về Development cho tất cả các trường hợp còn lại
    return "config.development"
