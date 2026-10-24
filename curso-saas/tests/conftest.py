import pytest

from app import create_app
from app.extensions import db
from app.models import Automation, InstagramAccount, User

PASSWORD = "password123"


class ConfigForTests:
    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # база в памяти, ничего не пишется на диск
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False  # в обычных тестах CSRF выключен, отдельный тест его включает
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class ConfigWithCsrf(ConfigForTests):
    WTF_CSRF_ENABLED = True


@pytest.fixture
def app():
    app = create_app(ConfigForTests)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def csrf_app():
    app = create_app(ConfigWithCsrf)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    """Создаёт пользователя напрямую в базе, возвращает его id."""
    def _make(email="user@example.com", password=PASSWORD):
        with app.app_context():
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user.id
    return _make


@pytest.fixture
def make_account(app):
    def _make(user_id, username):
        with app.app_context():
            account = InstagramAccount(user_id=user_id, username=username)
            db.session.add(account)
            db.session.commit()
            return account.id
    return _make


@pytest.fixture
def make_automation(app):
    def _make(user_id, keyword="Курс", direct_message="Привет! Вот ссылка.", **extra):
        with app.app_context():
            item = Automation(user_id=user_id, keyword=keyword,
                              direct_message=direct_message, **extra)
            db.session.add(item)
            db.session.commit()
            return item.id
    return _make


@pytest.fixture
def get_automation(app):
    def _get(automation_id):
        with app.app_context():
            return db.session.get(Automation, automation_id)
    return _get


@pytest.fixture
def login():
    def _login(client, email, password=PASSWORD):
        return client.post("/login", data={"email": email, "password": password})
    return _login
