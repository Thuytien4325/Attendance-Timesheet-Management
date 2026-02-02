import os

def get_settings_module() -> str:
    # Lấy giá trị môi trường, mặc định là 'development'
    env = os.getenv("APP_ENV", "development").lower()

    # Kiểm tra các điều kiện môi trường
    if env in {"prod", "production"}:
        return "config.production"
    
    if env in {"test", "testing"}:
        return "config.testing"
    
    # Mặc định cho dev và các trường hợp khác
    return "config.development"
