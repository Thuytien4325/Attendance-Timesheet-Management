import os


def get_settings_module() -> str:
    env = os.getenv("APP_ENV", "development").lower()
    if env in {"config", "settings"}:
        return "config.config"
    if env in {"dev", "development"}:
        return "config.development"
    if env in {"prod", "production"}:
        return "config.production"
    if env in {"test", "testing"}:
        return "config.testing"
    return "config.development"
