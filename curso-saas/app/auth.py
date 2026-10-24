"""Регистрация, вход и выход."""
from urllib.parse import urlsplit

from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .forms import LoginForm, RegisterForm
from .models import User

bp = Blueprint("auth", __name__)

# Нужен, чтобы вход с несуществующим email занимал столько же времени,
# сколько вход с существующим (так сложнее подбирать email'ы).
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _safe_next(target):
    """Разрешаем переходить только на страницы нашего сайта."""
    if not target or "\\" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            # Два одинаковых запроса одновременно: email уже занят.
            db.session.rollback()
            form.email.errors = list(form.email.errors) + ["Этот email уже зарегистрирован."]
        else:
            login_user(user)
            flash("Добро пожаловать! Аккаунт создан.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(email=form.email.data)
        ).scalar_one_or_none()

        if user is not None:
            password_ok = user.check_password(form.password.data)
        else:
            check_password_hash(_DUMMY_HASH, form.password.data)
            password_ok = False

        if password_ok:
            login_user(user, remember=form.remember.data)
            return redirect(_safe_next(request.args.get("next")) or url_for("main.dashboard"))
        flash("Неверный email или пароль.", "error")
    return render_template("login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.index"))
