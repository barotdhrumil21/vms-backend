import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vms_backend.settings')

app = Celery('vms_backend_server',broker=settings.CELERY_BROKER_URL)
app.conf.enable_utc = False
app.conf.update(
    timezone = 'Asia/Kolkata',
    task_serializer='json',
    accept_content=['json'],  
    result_serializer='json',
)
app.config_from_object('django.conf:settings', namespace = 'CELERY')

# Celery Beat Settings
app.conf.beat_schedule = {}

app.autodiscover_tasks()

@app.task(bind = True)
def debug_task(self):
    print(f'Request : {self.request!r}')