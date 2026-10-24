"""Заготовка для подключения Instagram через официальный API Meta (ЭТАП 2).

Сейчас здесь НЕТ реальных запросов к Meta. Функции только описывают,
что нужно будет сделать дальше. Ничего не выдумываем: точные адреса,
права доступа и формат подписи вебхуков возьмём из официальной
документации Meta for Developers, когда дойдём до этого этапа.

Нужные переменные окружения (см. .env.example):
    META_APP_ID, META_APP_SECRET, META_REDIRECT_URI, META_WEBHOOK_VERIFY_TOKEN
"""
import os

STATUS_NOT_CONNECTED = "not_connected"

STATUS_LABELS = {
    STATUS_NOT_CONNECTED: "Пока не подключено",
}

_REQUIRED_ENV = ("META_APP_ID", "META_APP_SECRET", "META_REDIRECT_URI")


def is_configured() -> bool:
    """Заданы ли настройки приложения Meta в переменных окружения."""
    return all(os.environ.get(name) for name in _REQUIRED_ENV)


def build_authorization_url(state: str) -> str:
    """ЭТАП 2: собрать ссылку, куда отправим пользователя для входа в Instagram."""
    raise NotImplementedError("OAuth Instagram будет добавлен на следующем этапе.")


def handle_oauth_callback(code: str, state: str):
    """ЭТАП 2: обработать возврат пользователя от Meta и сохранить аккаунт."""
    raise NotImplementedError("OAuth Instagram будет добавлен на следующем этапе.")


def handle_webhook_event(payload: dict) -> None:
    """ЭТАП 2: обработать событие (например, новый комментарий) и найти подходящие автоматизации."""
    raise NotImplementedError("Вебхуки Instagram будут добавлены на следующем этапе.")
