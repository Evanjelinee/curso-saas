from app.extensions import db
from app.models import Automation


def _all(app):
    with app.app_context():
        return db.session.query(Automation).all()


def _valid_data(**overrides):
    data = {
        "instagram_account_id": "0",
        "keyword": "Курс",
        "direct_message": "Привет! Вот ссылка на курс.",
        "public_reply": "Отправили в Direct!",
        "is_active": "y",
    }
    data.update(overrides)
    return data


def _logged_in(client, make_user, login):
    user_id = make_user("a@example.com")
    login(client, "a@example.com")
    return user_id


def test_create_automation(client, app, make_user, login):
    user_id = _logged_in(client, make_user, login)

    response = client.post("/automations/new", data=_valid_data())
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/automations")

    items = _all(app)
    assert len(items) == 1
    item = items[0]
    assert item.user_id == user_id
    assert item.keyword == "Курс"
    assert item.direct_message == "Привет! Вот ссылка на курс."
    assert item.public_reply == "Отправили в Direct!"
    assert item.is_active is True
    assert item.instagram_account_id is None

    page = client.get("/automations").get_data(as_text=True)
    assert "Курс" in page


def test_public_reply_is_optional(client, app, make_user, login):
    _logged_in(client, make_user, login)
    response = client.post("/automations/new", data=_valid_data(public_reply=""))
    assert response.status_code == 302
    assert _all(app)[0].public_reply is None


def test_create_disabled_automation(client, app, make_user, login):
    _logged_in(client, make_user, login)
    data = _valid_data()
    del data["is_active"]  # галочка не отмечена
    client.post("/automations/new", data=data)
    assert _all(app)[0].is_active is False


def test_keyword_is_trimmed(client, app, make_user, login):
    _logged_in(client, make_user, login)
    client.post("/automations/new", data=_valid_data(keyword="  Курс  "))
    assert _all(app)[0].keyword == "Курс"


def test_validation_errors_do_not_save(client, app, make_user, login):
    _logged_in(client, make_user, login)
    bad_inputs = [
        _valid_data(keyword=""),
        _valid_data(keyword="   "),
        _valid_data(direct_message=""),
        _valid_data(keyword="а" * 101),
        _valid_data(direct_message="а" * 1001),
        _valid_data(public_reply="а" * 301),
    ]
    for data in bad_inputs:
        response = client.post("/automations/new", data=data)
        assert response.status_code == 200
    assert _all(app) == []


def test_edit_automation(client, app, make_user, make_automation, login):
    user_id = _logged_in(client, make_user, login)
    automation_id = make_automation(user_id)

    response = client.post(
        f"/automations/{automation_id}/edit",
        data=_valid_data(keyword="Гайд", direct_message="Новый текст", public_reply=""),
    )
    assert response.status_code == 302
    item = _all(app)[0]
    assert item.keyword == "Гайд"
    assert item.direct_message == "Новый текст"
    assert item.public_reply is None


def test_edit_page_shows_current_values(client, make_user, make_automation, login):
    user_id = _logged_in(client, make_user, login)
    automation_id = make_automation(user_id, keyword="Секретное слово")
    page = client.get(f"/automations/{automation_id}/edit").get_data(as_text=True)
    assert "Секретное слово" in page


def test_toggle_automation(client, make_user, make_automation, get_automation, login):
    user_id = _logged_in(client, make_user, login)
    automation_id = make_automation(user_id, is_active=True)

    client.post(f"/automations/{automation_id}/toggle")
    assert get_automation(automation_id).is_active is False

    client.post(f"/automations/{automation_id}/toggle")
    assert get_automation(automation_id).is_active is True


def test_delete_automation(client, app, make_user, make_automation, login):
    user_id = _logged_in(client, make_user, login)
    automation_id = make_automation(user_id)

    response = client.post(f"/automations/{automation_id}/delete")
    assert response.status_code == 302
    assert _all(app) == []


def test_toggle_and_delete_require_post(client, make_user, make_automation, login):
    user_id = _logged_in(client, make_user, login)
    automation_id = make_automation(user_id)
    assert client.get(f"/automations/{automation_id}/toggle").status_code == 405
    assert client.get(f"/automations/{automation_id}/delete").status_code == 405


def test_accounts_page_shows_not_connected_status(client, make_user, login):
    _logged_in(client, make_user, login)
    page = client.get("/accounts").get_data(as_text=True)
    assert "Пока не подключено" in page
