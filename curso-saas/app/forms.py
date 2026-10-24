"""Формы и проверка вводимых данных."""
from flask_wtf import FlaskForm
from wtforms import (BooleanField, PasswordField, SelectField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                Optional, ValidationError)

from .extensions import db
from .models import User


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _clean_email(value):
    return value.strip().lower() if isinstance(value, str) else value


class RegisterForm(FlaskForm):
    email = StringField(
        "Email",
        filters=[_clean_email],
        validators=[
            DataRequired("Введите email."),
            Length(max=254, message="Email слишком длинный."),
            Email("Введите настоящий email, например name@example.com."),
        ],
    )
    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired("Введите пароль."),
            Length(min=8, max=128, message="Пароль должен быть от 8 до 128 символов."),
        ],
    )
    confirm = PasswordField(
        "Повторите пароль",
        validators=[
            DataRequired("Повторите пароль."),
            EqualTo("password", message="Пароли не совпадают."),
        ],
    )
    submit = SubmitField("Зарегистрироваться")

    def validate_email(self, field):
        exists = db.session.execute(
            db.select(User.id).filter_by(email=field.data)
        ).first()
        if exists:
            raise ValidationError("Этот email уже зарегистрирован.")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        filters=[_clean_email],
        validators=[DataRequired("Введите email."), Length(max=254)],
    )
    password = PasswordField(
        "Пароль",
        validators=[DataRequired("Введите пароль."), Length(max=128)],
    )
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class OwnAccountSelect(SelectField):
    """Список аккаунтов с понятным сообщением об ошибке на русском."""

    def pre_validate(self, form):
        allowed = {value for value, _label in self.choices}
        if self.data not in allowed:
            raise ValidationError("Выберите аккаунт из списка.")


class AutomationForm(FlaskForm):
    # Варианты выбора заполняются во view и содержат ТОЛЬКО аккаунты текущего
    # пользователя, поэтому чужой аккаунт выбрать нельзя.
    instagram_account_id = OwnAccountSelect(
        "Instagram-аккаунт", coerce=int, default=0, choices=[(0, "Все аккаунты")],
    )
    keyword = StringField(
        "Ключевое слово в комментарии",
        filters=[_strip],
        validators=[
            DataRequired("Введите ключевое слово."),
            Length(max=100, message="Не длиннее 100 символов."),
        ],
    )
    direct_message = TextAreaField(
        "Текст автоматического Direct",
        filters=[_strip],
        validators=[
            DataRequired("Введите текст сообщения."),
            Length(max=1000, message="Не длиннее 1000 символов."),
        ],
    )
    public_reply = StringField(
        "Публичный ответ на комментарий (необязательно)",
        filters=[_strip],
        validators=[Optional(), Length(max=300, message="Не длиннее 300 символов.")],
    )
    is_active = BooleanField("Автоматизация включена", default=True)
    submit = SubmitField("Сохранить")
