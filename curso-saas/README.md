# Curso — сервис автоответов в Instagram (этап 1)

Первая версия: регистрация, вход, личный кабинет, страница Instagram-аккаунтов
(пока со статусом «Пока не подключено») и создание автоматизаций.
Реальное подключение к Instagram (Meta) будет на следующем этапе.

## Что внутри

```
app/            код сайта (модели, формы, страницы, шаблоны, стили)
app/instagram.py  заготовка под будущий OAuth и вебхуки (пока без запросов к Meta)
migrations/     создание таблиц в базе
tests/          автоматические тесты
wsgi.py         точка входа для Gunicorn
render.yaml     настройки для Render
.env.example    пример переменных окружения (без секретов)
```

## 1. Запуск у себя на компьютере

Нужен Python 3.12 или новее.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Откройте файл `.env` и впишите в `SECRET_KEY` случайную строку. Получить её:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

`DATABASE_URL` можно оставить пустым: тогда создастся простой файл `local.db`.

Создайте таблицы и запустите сайт:

```bash
# Mac/Linux:
export FLASK_APP=wsgi.py
# Windows (PowerShell):  $env:FLASK_APP="wsgi.py"

flask db upgrade
flask run
```

Откройте http://127.0.0.1:5000

## 2. Тесты

```bash
pytest
```

Все тесты должны пройти (зелёные). Тесты не трогают вашу базу.

## 3. Загрузка на GitHub

Проще всего через терминал в папке проекта:

```bash
git init
git add .
git commit -m "Первая версия сайта"
git branch -M main
git remote add origin https://github.com/Evanjelinee/curso-saas.git
git push -u origin main
```

Перед `git add .` убедитесь, что файла `.env` нет в списке (`git status`). Он уже
указан в `.gitignore`, поэтому на GitHub не попадёт.

Без терминала: на странице репозитория нажмите **Add file → Upload files**
и перетащите содержимое папки (саму папку `.env` не загружайте).

## 4. Развёртывание на Render

**Вариант А (проще): через `render.yaml`**

1. На render.com нажмите **New → Blueprint** и выберите репозиторий `curso-saas`.
2. Render сам создаст сайт и базу PostgreSQL и подставит `DATABASE_URL` и `SECRET_KEY`.
3. Нажмите **Apply** и дождитесь зелёного статуса **Live**.

**Вариант Б: вручную**

1. **New → PostgreSQL**, имя `curso-saas-db`. После создания скопируйте **Internal Database URL**.
2. **New → Web Service**, выберите репозиторий.
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `flask db upgrade && gunicorn wsgi:app --bind 0.0.0.0:$PORT`
3. В разделе **Environment** добавьте:

| Переменная | Значение |
|---|---|
| `SECRET_KEY` | длинная случайная строка (см. выше) |
| `DATABASE_URL` | Internal Database URL из шага 1 |
| `APP_ENV` | `production` |
| `FLASK_APP` | `wsgi.py` |
| `PYTHON_VERSION` | `3.12.8` |

Проверка: откройте адрес сайта на Render, зарегистрируйтесь и создайте автоматизацию.

Условия бесплатных тарифов Render (в том числе срок жизни бесплатной базы) меняются:
проверьте их на render.com перед запуском.

## Безопасность

- Пароли хранятся только в виде хеша.
- Все формы защищены CSRF-токеном.
- Секреты лежат в переменных окружения, а не в коде.
- Каждый пользователь видит и меняет только свои аккаунты и автоматизации.
