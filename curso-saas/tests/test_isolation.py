"""Главная проверка безопасности: пользователь видит только свои данные."""


def _two_users(client, make_user, login):
    alice_id = make_user("alice@example.com")
    bob_id = make_user("bob@example.com")
    login(client, "bob@example.com")  # в клиенте вошёл Bob
    return alice_id, bob_id


def test_automations_list_shows_only_own(client, make_user, make_automation, login):
    alice_id, bob_id = _two_users(client, make_user, login)
    make_automation(alice_id, keyword="ТолькоАлиса")
    make_automation(bob_id, keyword="ТолькоБоб")

    page = client.get("/automations").get_data(as_text=True)
    assert "ТолькоБоб" in page
    assert "ТолькоАлиса" not in page


def test_cannot_open_or_edit_foreign_automation(client, make_user, make_automation,
                                                get_automation, login):
    alice_id, _ = _two_users(client, make_user, login)
    foreign_id = make_automation(alice_id, keyword="ТолькоАлиса")

    assert client.get(f"/automations/{foreign_id}/edit").status_code == 404

    response = client.post(f"/automations/{foreign_id}/edit", data={
        "instagram_account_id": "0", "keyword": "Взлом",
        "direct_message": "Взлом", "is_active": "y",
    })
    assert response.status_code == 404
    assert get_automation(foreign_id).keyword == "ТолькоАлиса"


def test_cannot_toggle_foreign_automation(client, make_user, make_automation,
                                          get_automation, login):
    alice_id, _ = _two_users(client, make_user, login)
    foreign_id = make_automation(alice_id, is_active=True)

    assert client.post(f"/automations/{foreign_id}/toggle").status_code == 404
    assert get_automation(foreign_id).is_active is True


def test_cannot_delete_foreign_automation(client, make_user, make_automation,
                                          get_automation, login):
    alice_id, _ = _two_users(client, make_user, login)
    foreign_id = make_automation(alice_id)

    assert client.post(f"/automations/{foreign_id}/delete").status_code == 404
    assert get_automation(foreign_id) is not None


def test_accounts_page_shows_only_own_accounts(client, make_user, make_account, login):
    alice_id, bob_id = _two_users(client, make_user, login)
    make_account(alice_id, "alice_shop")
    make_account(bob_id, "bob_shop")

    page = client.get("/accounts").get_data(as_text=True)
    assert "bob_shop" in page
    assert "alice_shop" not in page


def test_cannot_attach_foreign_account_to_automation(client, app, make_user, make_account, login):
    from app.extensions import db
    from app.models import Automation

    alice_id, _ = _two_users(client, make_user, login)
    foreign_account_id = make_account(alice_id, "alice_shop")

    response = client.post("/automations/new", data={
        "instagram_account_id": str(foreign_account_id),
        "keyword": "Курс", "direct_message": "Привет", "is_active": "y",
    })
    assert response.status_code == 200  # форма вернулась с ошибкой
    with app.app_context():
        assert db.session.query(Automation).count() == 0


def test_dashboard_counts_only_own_data(client, make_user, make_automation, login):
    alice_id, bob_id = _two_users(client, make_user, login)
    make_automation(alice_id, keyword="A1")
    make_automation(alice_id, keyword="A2")
    make_automation(bob_id, keyword="B1")

    page = client.get("/dashboard").get_data(as_text=True)
    # у Bob одна автоматизация (число 1 в карточке), а не три
    assert '<div class="stat-number">1</div>' in page
    assert '<div class="stat-number">2</div>' not in page
    assert '<div class="stat-number">3</div>' not in page
