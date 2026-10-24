"""Главная, личный кабинет, Instagram-аккаунты и автоматизации."""
from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from . import instagram
from .extensions import db
from .forms import AutomationForm
from .models import Automation, InstagramAccount

bp = Blueprint("main", __name__)


def _own_accounts():
    return db.session.execute(
        db.select(InstagramAccount)
        .filter_by(user_id=current_user.id)
        .order_by(InstagramAccount.created_at.desc())
    ).scalars().all()


def _own_automation_or_404(automation_id: int) -> Automation:
    """Находит автоматизацию ТОЛЬКО среди правил текущего пользователя."""
    automation = db.session.execute(
        db.select(Automation).filter_by(id=automation_id, user_id=current_user.id)
    ).scalar_one_or_none()
    if automation is None:
        # Чужое правило и несуществующее выглядят одинаково: 404.
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
