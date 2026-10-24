"""Интеграция с Meta Instagram Graph API (этап 2).

OAuth через Login with Facebook, шифрование токенов, вебхуки, DM и ответы.
Никакие токены и сырые payload не пишутся в логи.
"""
import base64
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .extensions import db
from .models import Automation, InstagramAccount, WebhookEvent

logger = logging.getLogger(__name__)

STATUS_NOT_CONNECTED = "not_connected"
STATUS_CONNECTED = "connected"
STATUS_TOKEN_EXPIRED = "token_expired"
STATUS_ERROR = "error"

STATUS_LABELS = {
    STATUS_NOT_CONNECTED: "Пока не подключено",
    STATUS_CONNECTED: "Подключено",
    STATUS_TOKEN_EXPIRED: "Токен истёк",
    STATUS_ERROR: "Ошибка",
}

# Официальные endpoints Meta (v18.0)
META_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
META_GRAPH_API = "https://graph.facebook.com/v18.0"

# Разрешения, нужные для задачи
REQUIRED_PERMISSIONS = [
    "pages_show_list",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_manage_comments",
    "instagram_manage_messages",   # для Direct
    "pages_manage_metadata",       # для подписки на вебхуки
]

_REQUIRED_ENV = (
    "META_APP_ID",
    "META_APP_SECRET",
    "META_REDIRECT_URI",
    "META_WEBHOOK_VERIFY_TOKEN",
    "TOKEN_ENCRYPTION_KEY",
)


# ---------- Шифрование токенов ----------

def _get_encryption_key() -> bytes:
    secret = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not secret:
        raise RuntimeError("Не задана переменная окружения TOKEN_ENCRYPTION_KEY")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"curso-saas-instagram-tokens-v1",
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))


def encrypt_token(token: str) -> str:
    if not token:
        return ""
    f = Fernet(_get_encryption_key())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    try:
        f = Fernet(_get_encryption_key())
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception:
        # Намеренно не логируем содержимое — это токен.
        logger.exception("Не удалось расшифровать токен")
        return ""


# ---------- Проверка конфигурации ----------

def is_configured() -> bool:
    return all(os.environ.get(name) for name in _REQUIRED_ENV)


# ---------- OAuth ----------

def build_authorization_url(state: str) -> str:
    params = {
        "client_id": os.environ["META_APP_ID"],
        "redirect_uri": os.environ["META_REDIRECT_URI"],
        "state": state,
        "scope": ",".join(REQUIRED_PERMISSIONS),
        "response_type": "code",
    }
    return f"{META_AUTH_URL}?{urlencode(params)}"


def _meta_get(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Meta API: {data['error'].get('message', 'unknown')}")
    return data


def _exchange_code(code: str) -> str:
    """Authorization code → short-lived token."""
    data = _meta_get(META_TOKEN_URL, {
        "client_id": os.environ["META_APP_ID"],
        "client_secret": os.environ["META_APP_SECRET"],
        "redirect_uri": os.environ["META_REDIRECT_URI"],
        "code": code,
    })
    return data["access_token"]


def _exchange_long_lived(short_token: str) -> tuple[str, int]:
    """Short-lived token → long-lived (≈60 дней). Возвращает (token, seconds)."""
    data = _meta_get(META_TOKEN_URL, {
        "grant_type": "fb_exchange_token",
        "client_id": os.environ["META_APP_ID"],
        "client_secret": os.environ["META_APP_SECRET"],
        "fb_exchange_token": short_token,
    })
    return data["access_token"], int(data.get("expires_in", 5_184_000))


def _get_page_id(user_token: str) -> str | None:
    data = _meta_get(f"{META_GRAPH_API}/me/accounts", {
        "fields": "id",
        "access_token": user_token,
    })
    pages = data.get("data", [])
    return pages[0]["id"] if pages else None


def _get_page_token(user_token: str, page_id: str) -> str:
    data = _meta_get(f"{META_GRAPH_API}/{page_id}", {
        "fields": "access_token",
        "access_token": user_token,
    })
    return data["access_token"]


def _get_ig_account_for_page(page_token: str, page_id: str) -> dict | None:
    data = _meta_get(f"{META_GRAPH_API}/{page_id}", {
        "fields": "instagram_business_account{id,username}",
        "access_token": page_token,
    })
    return data.get("instagram_business_account")


def handle_oauth_callback(code: str, state: str, user_id: int) -> InstagramAccount:
    """Обработать возврат от Meta: обменять код, получить IG-аккаунт, сохранить."""
    short_token = _exchange_code(code)
    long_token, expires_in = _exchange_long_lived(short_token)

    page_id = _get_page_id(long_token)
    if not page_id:
        raise RuntimeError(
            "Не удалось получить Facebook-страницу. "
            "Убедитесь, что Instagram переключён на профессиональный "
            "и привязан к странице, где вы — администратор."
        )

    page_token = _get_page_token(long_token, page_id)
    ig_account = _get_ig_account_for_page(page_token, page_id)
    if not ig_account:
        raise RuntimeError(
            "У этой страницы нет подключённого Instagram-аккаунта. "
            "Привяжите профессиональный Instagram к странице в настройках Facebook."
        )

    ig_user_id = ig_account["id"]
    username = ig_account.get("username", "unknown")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    existing = db.session.execute(
        db.select(InstagramAccount).filter_by(ig_user_id=ig_user_id)
    ).scalar_one_or_none()

    if existing:
        # Переподключение: обновляем токен и статус, владельца не меняем.
        if existing.user_id != user_id:
            raise RuntimeError(
                "Этот Instagram-аккаунт уже подключён другим пользователем."
            )
        existing.username = username
        existing.page_id = page_id
        existing.access_token_encrypted = encrypt_token(long_token)
        existing.token_expires_at = expires_at
        existing.status = STATUS_CONNECTED
        db.session.commit()
        return existing

    account = InstagramAccount(
        user_id=user_id,
        username=username,
        status=STATUS_CONNECTED,
        ig_user_id=ig_user_id,
        page_id=page_id,
        access_token_encrypted=encrypt_token(long_token),
        token_expires_at=expires_at,
    )
    db.session.add(account)
    db.session.commit()
    return account


# ---------- Webhooks ----------

def verify_webhook_challenge(mode: str, token: str, challenge: str) -> bool:
    if mode != "subscribe":
        return False
    verify_token = os.environ.get("META_WEBHOOK_VERIFY_TOKEN")
    return bool(verify_token) and hmac.compare_digest(verify_token, token)


def verify_webhook_signature(payload: bytes, signature: str | None) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    app_secret = os.environ.get("META_APP_SECRET")
    if not app_secret:
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def process_webhook_event(payload: dict) -> None:
    """Разобрать payload Meta и обработать изменения комментариев."""
    if payload.get("object") != "instagram":
        return

    for entry in payload.get("entry", []):
        ig_user_id = entry.get("id")  # ID Instagram-аккаунта
        if not ig_user_id:
            continue

        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            value = change.get("value", {})
            comment_id = value.get("id")
            if not comment_id:
                continue

            # Дедупликация
            if db.session.execute(
                db.select(WebhookEvent.id).filter_by(event_id=comment_id)
            ).scalar_one_or_none():
                continue
            db.session.add(WebhookEvent(event_id=comment_id))
            db.session.commit()

            _handle_comment(ig_user_id, value)


def _handle_comment(ig_user_id: str, comment_data: dict) -> None:
    """Найти автоматизации ТОЛЬКО владельца этого IG-аккаунта и выполнить их."""
    account = db.session.execute(
        db.select(InstagramAccount).filter_by(ig_user_id=ig_user_id)
    ).scalar_one_or_none()
    if not account or account.status != STATUS_CONNECTED:
        return

    access_token = decrypt_token(account.access_token_encrypted)
    if not access_token:
        return

    comment_id = comment_data.get("id")
    text = (comment_data.get("text") or "").lower()
    sender_id = comment_data.get("from", {}).get("id")
    if not (comment_id and text and sender_id):
        return

    # Ищем правила ТОЛЬКО владельца аккаунта — строгая изоляция.
    automations = db.session.execute(
        db.select(Automation).where(
            Automation.user_id == account.user_id,
            Automation.is_active.is_(True),
            db.or_(
                Automation.instagram_account_id == account.id,
                Automation.instagram_account_id.is_(None),
            ),
        )
    ).scalars().all()

    for automation in automations:
        if automation.keyword.lower() not in text:
            continue

        if automation.public_reply:
            try:
                _reply_to_comment(comment_id, automation.public_reply, access_token)
            except Exception:
                logger.exception("Не удалось ответить на комментарий %s", comment_id)

        try:
            _send_direct(account.ig_user_id, sender_id, automation.direct_message, access_token)
        except Exception:
            logger.exception("Не удалось отправить Direct пользователю %s", sender_id)


def _reply_to_comment(comment_id: str, reply: str, access_token: str) -> None:
    r = requests.post(
        f"{META_GRAPH_API}/{comment_id}/comments",
        data={"message": reply, "access_token": access_token},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "unknown"))


def _send_direct(ig_account_id: str, recipient_id: str, message: str, access_token: str) -> None:
    r = requests.post(
        f"{META_GRAPH_API}/{ig_account_id}/messages",
        json={
            "recipient": {"id": recipient_id},
            "message": {"text": message},
            "access_token": access_token,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "unknown"))
