"""Главная, личный кабинет, Instagram-аккаунты и автоматизации."""
import secrets
from flask import (
    Blueprint, abort, flash, redirect, render_template,
    request, session, url_for,
)
from flask_login import current_user, login_required

from . import instagram
from .extensions import csrf, db
from .forms import AutomationForm
from .models import Automation, InstagramAccount

bp = Blueprint("main", __name__)


def _own_accounts():
    return db.session.execute(
        db.select(InstagramAccount)
        .filter_by(user_id=current_user.id)
        .order_by(InstagramAccount.created_at.desc())
    ).scalars().all()


def _own_account_or_404(account_id: int) -> InstagramAccount:
    account = db.session.execute(
        db.select(InstagramAccount).filter_by(id=account_id, user_id=current_user.id)
    ).scalar_one_or_none()
    if account is None:
        abort(404)
    return account


def _own_automation_or_404(automation_id: int) -> Automation:
    automation = db.session.execute(
        db.select(Automation).filter_by(id=automation_id, user_id=current_user.id)
    ).scalar_one_or_none()
    if automation is None:
        abort(404)
    return automation


def _fill_account_choices(form: AutomationForm, accounts) -> None:
    form.instagram_account_id.choices = [(0, "Все аккаунты")] + [
        (a.id, "@" + a.username) for a in accounts
    ]


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@bp.route("/healthz")
def healthz():
    return "ok"


@bp.route("/dashboard")
@login_required
def dashboard():
    automations = db.session.execute(
        db.select(Automation).filter_by(user_id=current_user.id)
    ).scalars().all()
    return render_template(
        "dashboard.html",
        accounts_count=len(_own_accounts()),
        automations_count=len(automations),
        active_count=sum(1 for a in automations if a.is_active),
    )


@bp.route("/accounts")
@login_required
def accounts():
    return render_template(
        "accounts.html",
        accounts=_own_accounts(),
        status_labels=instagram.STATUS_LABELS,
    )


@bp.route("/accounts/connect")
@login_required
def accounts_connect():
    if not instagram.is_configured():
        flash("Интеграция с Instagram пока не настроена администратором.", "error")
        return redirect(url_for("main.accounts"))

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    return redirect(instagram.build_authorization_url(state))


@bp.route("/accounts/callback")
@login_required
def accounts_callback():
    state = request.args.get("state")
    expected = session.pop("oauth_state", None)
    if not state or not expected or not secrets.compare_digest(state, expected):
        flash("Ошибка безопасности. Попробуйте подключиться снова.", "error")
        return redirect(url_for("main.accounts"))

    if request.args.get("error"):
        flash(f"Meta вернул ошибку: {request.args['error']}", "error")
        return redirect(url_for("main.accounts"))

    code = request.args.get("code")
    if not code:
        flash("Не получен код авторизации.", "error")
        return redirect(url_for("main.accounts"))

    try:
        account = instagram.handle_oauth_callback(code, state, current_user.id)
        flash(f"Instagram-аккаунт @{account.username} подключён.", "success")
    except Exception as e:
        flash(f"Не удалось подключить Instagram: {e}", "error")

    return redirect(url_for("main.accounts"))


@bp.route("/accounts/<int:account_id>/disconnect", methods=["POST"])
@login_required
def accounts_disconnect(account_id: int):
    account = _own_account_or_404(account_id)
    account.access_token_encrypted = None
    account.token_expires_at = None
    account.ig_user_id = None
    account.page_id = None
    account.status = instagram.STATUS_NOT_CONNECTED
    db.session.commit()
    flash(f"Instagram-аккаунт @{account.username} отключён.", "info")
    return redirect(url_for("main.accounts"))


# ---------- Webhooks Meta (без аутентификации пользователя) ----------

@bp.route("/instagram/webhook", methods=["GET"])
def instagram_webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if instagram.verify_webhook_challenge(mode, token, challenge):
        return challenge, 200
    return "Verification failed", 403


@bp.route("/instagram/webhook", methods=["POST"])
@csrf.exempt
def instagram_webhook_event():
    signature = request.headers.get("X-Hub-Signature-256")
    if not instagram.verify_webhook_signature(request.data, signature):
        return "Invalid signature", 401

    try:
        instagram.process_webhook_event(request.get_json(silent=True) or {})
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Ошибка обработки webhook")

    return "OK", 200


# ---------- Автоматизации (без изменений логики) ----------

@bp.route("/automations")
@login_required
def automations():
    items = db.session.execute(
        db.select(Automation)
        .filter_by(user_id=current_user.id)
        .order_by(Automation.created_at.desc(), Automation.id.desc())
    ).scalars().all()
    return render_template("automations.html", automations=items)


@bp.route("/automations/new", methods=["GET", "POST"])
@login_required
def automation_new():
    form = AutomationForm()
    _fill_account_choices(form, _own_accounts())
    if form.validate_on_submit():
        automation = Automation(
            user_id=current_user.id,
            instagram_account_id=form.instagram_account_id.data or None,
            keyword=form.keyword.data,
            direct_message=form.direct_message.data,
            public_reply=form.public_reply.data or None,
            is_active=form.is_active.data,
        )
        db.session.add(automation)
        db.session.commit()
        flash("Автоматизация создана.", "success")
        return redirect(url_for("main.automations"))
    return render_template("automation_form.html", form=form, title="Новая автоматизация")


@bp.route("/automations/<int:automation_id>/edit", methods=["GET", "POST"])
@login_required
def automation_edit(automation_id: int):
    automation = _own_automation_or_404(automation_id)
    form = AutomationForm(obj=automation)
    _fill_account_choices(form, _own_accounts())
    if form.validate_on_submit():
        automation.instagram_account_id = form.instagram_account_id.data or None
        automation.keyword = form.keyword.data
        automation.direct_message = form.direct_message.data
        automation.public_reply = form.public_reply.data or None
        automation.is_active = form.is_active.data
        db.session.commit()
        flash("Изменения сохранены.", "success")
        return redirect(url_for("main.automations"))
    if not form.is_submitted():
        form.instagram_account_id.data = automation.instagram_account_id or 0
    return render_template("automation_form.html", form=form, title="Редактирование автоматизации")


@bp.route("/automations/<int:automation_id>/toggle", methods=["POST"])
@login_required
def automation_toggle(automation_id: int):
    automation = _own_automation_or_404(automation_id)
    automation.is_active = not automation.is_active
    db.session.commit()
    flash("Автоматизация включена." if automation.is_active else "Автоматизация выключена.", "info")
    return redirect(url_for("main.automations"))


@bp.route("/automations/<int:automation_id>/delete", methods=["POST"])
@login_required
def automation_delete(automation_id: int):
    automation = _own_automation_or_404(automation_id)
    db.session.delete(automation)
    db.session.commit()
    flash("Автоматизация удалена.", "info")
    return redirect(url_for("main.automations"))
