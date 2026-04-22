# Hackathon Support Backend

Backend for a hackathon support system built with Django, Django ORM, Django admin, and Django REST Framework.

## Local Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Admin panel:

```text
http://127.0.0.1:8000/admin/
```

REST API:

```text
http://127.0.0.1:8000/api/users/
http://127.0.0.1:8000/api/teams/
http://127.0.0.1:8000/api/team-members/
```

## Database

SQLite is used by default for local development.

For PostgreSQL, set environment variables:

```bash
DB_ENGINE=django.db.backends.postgresql
DB_NAME=hackathon
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```
