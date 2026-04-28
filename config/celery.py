import os
from datetime import timedelta

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("hackathon")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "hackathon-schedule-notifications": {
        "task": "hackathon.tasks.process_hackathon_schedule_notifications",
        "schedule": timedelta(seconds=60),
    },
}
