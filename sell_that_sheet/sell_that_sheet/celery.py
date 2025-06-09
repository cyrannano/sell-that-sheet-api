import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sell_that_sheet.settings")

app = Celery("sell_that_sheet")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
