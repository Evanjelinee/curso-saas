"""Фабрика приложения Flask."""
import os
from flask import Flask, render_template
from .config import IS_PRODUCTION, Config
from .extensions import csrf, db, login_manager, migrate

def create_app(config_object=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object is not None:
        app.config.from_object(config_object)

    if not app.config.get("SECRET_KEY"):
        if IS_PRODUCTION:
            raise RuntimeError("Не задана переменная окружения SECRET_KEY.")
        app.config["SECRET_KEY"] = os.urandom(32).hex()

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401
    from .auth import bp as auth_bp
    from .main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    _register_error_handlers(app)
    _register_security_headers(app)

    return app


def _register_error_handlers(app: Flask) -> None:
    def show(code: int, title: str, message: str):
        return render_template("error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(_error):
        return show(400, "Не удалось обработать запрос", "Обновите страницу и попробуйте ещё раз.")

    @app.errorhandler(403)
    def forbidden(_error):
        return show(403, "Нет доступа", "У вас нет прав для этой страницы.")

    @app.errorhandler(404)
    def not_found(_error):
        return show(404, "Страница не найдена", "Такой страницы нет или она вам недоступна.")

    @app.errorhandler(413)
    def too_large(_error):
        return show(413, "Слишком большой запрос", "Отправьте меньше данных.")

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return show(500, "Что-то пошло не так", "Мы уже знаем о проблеме. Попробуйте позже.")


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response
