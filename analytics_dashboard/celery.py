# analytics_dashboard/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set default settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analytics_dashboard.settings')

app = Celery('analytics_dashboard')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
