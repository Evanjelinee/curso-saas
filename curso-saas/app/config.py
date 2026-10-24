"""Настройки приложения. Все секреты берутся из переменных окружения."""
import os
from datetime import timedelta

from dotenv import load_dotenv

# Локально читаем файл .env (на Render он не нужен, там свои переменные).
load_dotenv()


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        # Только для локального запуска. На Render всегда будет PostgreSQL.
        return "sqlite:///local.db"
    # Render может выдать адрес со старым началом "postgres://".
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


IS_PRODUCTION = os.environ.get("APP_ENV") == "production"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Безопасные cookie
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    # Ограничение размера запроса (1 МБ)
    MAX_CONTENT_LENGTH = 1024 * 1024

    # Время жизни CSRF-токена в форме (8 часов)
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8
