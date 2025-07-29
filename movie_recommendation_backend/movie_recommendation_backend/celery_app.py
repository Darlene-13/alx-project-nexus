"""
Celery configuration for the movie recommendation backend.

This file configurs celery for handling background tasks

For our movie_recommendation_backend project, this file sets up:
Movie data updates from external APIs
User recommendation generatiom
Email notifications
Push notifications
Analytics and data processing.
Database cleanup tasks.

"""

import os
from celery import Celery
from django.conf import settings

# SET the default Django settings module for the celery app
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recommendation_backend.settings')

app = Celery('movie_recommendation_backend')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# SETTINGS CONFIGURATION OF CELERY