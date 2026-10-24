from app.extensions import db
from app.models import User


def _count_users(app):
    with app.app_context():
        return db.session.query(User).count()


def _register(client, email="new@example.com", password="password123", confirm=None):
    return client.post("/register", data={
        "email": email,
        "password": password,
        "confirm": password if confirm is None else confirm,
    })


def test_register_success(client, app):
    response = _register(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert _count_users(app) == 1

    with app.app_context():
        user = db.session.query(User).one()
        assert user.email == "new@example.com"
        assert user.password_hash != "password123"  # пароль хранится как хеш
        assert user.check_password("password123")

    # После регистрации пользователь сразу вошёл
    assert client.get("/dashboard").status_code == 200


def test_register_duplicate_email_is_rejected(client, app):
    _register(client, email="same@example.com")
    client.post("/logout")
    response = _register(client, email="SAME@example.com")  # другой регистр
    assert response.status_code == 200
    assert "уже зарегистрирован" in response.get_data(as_text=True)
    assert _count_users(app) == 1


def test_register_short_password_is_rejected(client, app):
    response = _register(client, password="short")
    assert response.status_code == 200
    assert "от 8 до 128" in response.get_data(as_text=True)
    assert _count_users(app) == 0


def test_register_password_mismatch_is_rejected(client, app):
    response = _register(client, password="password123", confirm="different123")
    assert response.status_code == 200
    assert "Пароли не совпадают" in response.get_data(as_text=True)
    assert _count_users(app) == 0


def test_register_invalid_email_is_rejected(client, app):
    response = _register(client, email="not-an-email")
    assert response.status_code == 200
    assert _count_users(app) == 0


def test_login_success(client, make_user, login):
    make_user("a@example.com")
    response = login(client, "a@example.com")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert client.get("/dashboard").status_code == 200


def test_login_wrong_password(client, make_user, login):
    make_user("a@example.com")
    response = login(client, "a@example.com", "wrong-password")
    assert response.status_code == 200
    assert "Неверный email или пароль" in response.get_data(as_text=True)
    assert client.get("/dashboard").status_code == 302


def test_login_unknown_email_has_same_message(client, login):
    response = login(client, "nobody@example.com")
    assert response.status_code == 200
    assert "Неверный email или пароль" in response.get_data(as_text=True)


def test_login_does_not_redirect_to_other_sites(client, make_user):
    make_user("a@example.com")
    response = client.post("/login?next=https://evil.example.com/", data={
        "email": "a@example.com", "password": "password123",
    })
    assert response.status_code == 302
    assert "evil.example.com" not in response.headers["Location"]


def test_logout(client, make_user, login):
    make_user("a@example.com")
    login(client, "a@example.com")
    response = client.post("/logout")
    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 302


def test_logout_requires_post(client, make_user, login):
    make_user("a@example.com")
    login(client, "a@example.com")
    assert client.get("/logout").status_code == 405


def test_pages_require_login(client):
    for url in ("/dashboard", "/accounts", "/automations", "/automations/new"):
        response = client.get(url)
        assert response.status_code == 302, url
        assert "/login" in response.headers["Location"], url


def test_post_without_csrf_token_is_rejected(csrf_app):
    client = csrf_app.test_client()
    response = client.post("/register", data={
        "email": "x@example.com", "password": "password123", "confirm": "password123",
    })
    assert response.status_code == 400
    with csrf_app.app_context():
        assert db.session.query(User).count() == 0
