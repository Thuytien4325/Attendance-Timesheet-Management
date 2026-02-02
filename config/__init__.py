import os


def get_settings_module():
    env = os.getenv("APP_ENV", "development").lower()

    if env == "production":
        return "config.config"
    elif env == "test":
        return "config.config"
    else:
        return "config.config"
