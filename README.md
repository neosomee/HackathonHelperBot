# Hackathon Support Backend

Django backend for a hackathon support system. The project includes Django ORM models, Django admin, REST API endpoints, and a service layer that can be reused by a Telegram bot or Mini App.

## Stack

- Python 3.13
- Django 6
- Django REST Framework
- SQLite for quick local development
- PostgreSQL for Docker/local production-like setup

## Quick Start With SQLite

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create local environment file:

```bash
copy .env.example .env
```

Run migrations:

```bash
python manage.py migrate
```

Create admin user:

```bash
python manage.py createsuperuser
```

Start server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/admin/
http://127.0.0.1:8000/api/team/list/
```

## Quick Start With Docker

Start backend and PostgreSQL:

```bash
docker compose up --build
```

The backend container runs migrations automatically before starting the server.

Create admin user in Docker:

```bash
docker compose exec backend python manage.py createsuperuser
```

Stop containers:

```bash
docker compose down
```

Remove database volume too:

```bash
docker compose down -v
```

## Environment Variables

Copy `.env.example` to `.env` for local development. The project reads `.env` automatically from the repository root.

Important variables:

```text
DJANGO_SECRET_KEY=django-insecure-change-me
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

For PostgreSQL:

```text
DB_ENGINE=django.db.backends.postgresql
DB_NAME=hackathon
DB_USER=hackathon
DB_PASSWORD=hackathon
DB_HOST=localhost
DB_PORT=5432
```

Telegram bot variables:

```text
BOT_TOKEN=your-telegram-bot-token
BACKEND_API_URL=http://127.0.0.1:8000
MINI_APP_URL=
```

## Telegram Bot

The bot is stored in `bot/` and uses the backend REST API. It does not duplicate backend business logic.

Start the Django backend first:

```bash
python manage.py runserver
```

Then start the bot:

```bash
python -m bot.main
```

Current bot features:

- `/start` checks `GET /api/profile/<telegram_id>/`
- unregistered users go through registration FSM
- registration sends data to `POST /api/register/`
- registered users see the main menu
- the main menu opens Mini App via `MINI_APP_URL`
- profile button reads `GET /api/profile/<telegram_id>/`
- team creation, applications, team search, and team management are handled by Mini App

## API Endpoints

Users:

```text
POST /api/register/
GET  /api/profile/<telegram_id>/
POST /api/profile/update/
```

Teams:

```text
POST /api/team/create/
GET  /api/team/list/
GET  /api/team/<id>/
POST /api/team/apply/
```

Captain requests:

```text
GET  /api/team/requests/<captain_telegram_id>/
POST /api/team/decision/
```

Admin and generic DRF endpoints:

```text
GET /admin/
GET /api/users/
GET /api/teams/
GET /api/team-members/
```

## Roles

The backend uses one unified role list:

```text
PARTICIPANT
CAPTAIN
ORGANIZER
ADMIN
```

New users are created as `PARTICIPANT`. When a participant creates a team, their role becomes `CAPTAIN`.

## Business Rules

- One user can be an accepted member of only one team.
- A user cannot apply to the same team twice.
- A user cannot create a team if they are already a captain or an accepted team member.
- Only the team captain can accept or reject applications.
- Applications can be processed only while they are `pending`.
- When a team is created, its captain is automatically added to that team as `accepted`.

## Example Requests

Register or update user:

```json
{
  "telegram_id": 123456789,
  "full_name": "Ivan Ivanov",
  "email": "ivan@example.com",
  "skills": "Python, Django"
}
```

Update profile:

```json
{
  "telegram_id": 123456789,
  "full_name": "Ivan Ivanov",
  "email": "ivan@example.com",
  "skills": "Python, Django, REST API"
}
```

Create team:

```json
{
  "captain_telegram_id": 123456789,
  "name": "Backend Builders",
  "description": "We build a hackathon assistant",
  "tech_stack": "Python, Django, PostgreSQL",
  "vacancies": "Frontend, Designer"
}
```

Apply to team:

```json
{
  "user_telegram_id": 987654321,
  "team_id": 1
}
```

Accept or reject application:

```json
{
  "captain_telegram_id": 123456789,
  "user_telegram_id": 987654321,
  "team_id": 1,
  "decision": "accept"
}
```

## Useful Commands

Check project:

```bash
python manage.py check
```

Create migrations after model changes:

```bash
python manage.py makemigrations
```

Apply migrations:

```bash
python manage.py migrate
```

Run development server:

```bash
python manage.py runserver
```

## Project Structure

```text
config/              Django settings and root URLs
hackathon/           Main app with models, API views, serializers, admin, services
hackathon/services.py reusable business logic for API, bot, and Mini App
manage.py            Django management entrypoint
docker-compose.yml   Backend + PostgreSQL local stack
```
