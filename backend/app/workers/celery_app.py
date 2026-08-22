from celery import Celery

from app.config import settings

celery_app = Celery(
    "clinicbrain",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

from celery.schedules import crontab

celery_app.conf.task_default_queue = "default"
celery_app.conf.beat_schedule = {
    "followup-reminders-hourly": {
        "task": "whatsapp.followup_reminders",
        "schedule": crontab(minute=0),
    },
}
