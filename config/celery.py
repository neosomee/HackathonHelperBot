import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("HackathonHelperBot")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "process-hackathon-schedule-notifications-every-minute": {
        "task": "hackathon.tasks.process_hackathon_schedule_notifications",
        "schedule": 60.0,
    },
}