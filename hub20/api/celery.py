import os

from celery import Celery
from celery.schedules import crontab


class Hub20CeleryConfig:
    name = "Hub20"

    broker_url = "memory" if "HUB20_TEST" in os.environ else os.getenv("HUB20_BROKER_URL")
    broker_use_ssl = "HUB20_BROKER_USE_SSL" in os.environ
    beat_schedule = {
        "clear-expired-sessions": {
            "task": "hub20.apps.core.tasks.clear_expired_sessions",
            "schedule": crontab(minute="*/30"),
        },
        "execute-transfers": {
            "task": "hub20.apps.core.tasks.execute_pending_transfers",
            "schedule": crontab(),
        },
    }
    task_always_eager = "HUB20_TEST" in os.environ
    task_eager_propagates = "HUB20_TEST" in os.environ


app = Celery()
app.config_from_object(Hub20CeleryConfig)
app.autodiscover_tasks()
