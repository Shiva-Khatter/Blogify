# django_project/celery.py
import os
from celery import Celery

# Setting the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

app = Celery('django_project')

# Using a string here means the worker doesn't have to serialize 
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

#Loading task modules from all registered Django app Configs 
app.autodiscover_tasks()