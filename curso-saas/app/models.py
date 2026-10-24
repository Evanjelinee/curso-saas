"""Таблицы базы данных: пользователи, Instagram-аккаунты, автоматизации."""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    instagram_accounts = db.relationship(
        "InstagramAccount", back_populates="owner",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    automations = db.relationship(
        "Automation", back_populates="owner",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    def set_password(self, password: str) -> None:
        # В базе хранится только хеш, сам пароль не сохраняется.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class InstagramAccount(db.Model):
    """Подключённый Instagram-аккаунт.

    Сейчас (этап 1) подключение не работает, поэтому записей обычно нет.
    Поля для токена добавим на этапе 2 вместе с OAuth.
    """
    __tablename__ = "instagram_accounts"
    __table_args__ = (
        db.UniqueConstraint("user_id", "username", name="uq_instagram_accounts_user_username"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    username = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="not_connected")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    owner = db.relationship("User", back_populates="instagram_accounts")


class Automation(db.Model):
    """Правило: на комментарий с ключевым словом отправить Direct."""
    __tablename__ = "automations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Пусто (None) = правило для всех аккаунтов пользователя.
    instagram_account_id = db.Column(
        db.Integer, db.ForeignKey("instagram_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    keyword = db.Column(db.String(100), nullable=False)
    direct_message = db.Column(db.Text, nullable=False)
    public_reply = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False,
    )

    owner = db.relationship("User", back_populates="automations")
    instagram_account = db.relationship("InstagramAccount")


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
