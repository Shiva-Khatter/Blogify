import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
app = Celery('django_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Adding Beat schedule
app.conf.beat_schedule = {
    'process-scheduled-posts-every-minute': {
        'task': 'blog.tasks.process_scheduled_posts',
        'schedule': 60.0,  # Every 60 seconds (1 minute)
    },
}