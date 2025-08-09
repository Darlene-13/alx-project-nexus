"""
Celery configuration for the movie recommendation backend.

This file configures celery for handling background tasks

For our movie_recommendation_backend project, this file sets up:
- Movie data updates from external APIs
- User recommendation generation
- Email notifications
- Push notifications
- Analytics and data processing
- Database cleanup tasks

Background task queues:
- notifications: Email and push notifications
- analytics: User activity logging and metrics
- recommendations: Movie recommendation generation
- default: General purpose tasks
"""

import os
from celery import Celery
from celery.schedules import crontab

# SET the default Django settings module for the celery app
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recommendation_backend.settings')

# Create the Celery app instance
app = Celery('movie_recommendation_backend')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# CELERY CONFIGURATION SETTINGS

# Basic Configuration
app.conf.update(
    # Broker and Result Backend
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Serialization
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    
    # Timezone Configuration
    timezone='UTC',
    enable_utc=True,
    
    # Task Result Settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Worker Configuration
    worker_send_task_events=True,
    task_send_sent_event=True,
    worker_disable_rate_limits=False,
    worker_pool_restarts=True,
    
    # Task Routing and Queues (FIXED - removed core.tasks.*)
    task_routes={
        'apps.notifications.tasks.*': {'queue': 'notifications'},
        'apps.analytics.tasks.*': {'queue': 'analytics'}, 
        'apps.movies.tasks.*': {'queue': 'recommendations'},
    },
    
    # Task Execution Settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Retry Configuration
    task_default_retry_delay=60,    # 1 minute
    task_max_retries=3,
    task_retry_jitter=True,         # Add randomness to retries
    
    # Rate Limiting
    task_annotations={
        '*': {'rate_limit': '100/h'},  # Global rate limit
        'apps.notifications.tasks.send_email_task': {'rate_limit': '50/m'},
        'apps.analytics.tasks.log_user_activity_task': {'rate_limit': '200/m'},
        'apps.movies.tasks.update_movie_data': {'rate_limit': '10/m'},
    },
    
    # Redis-specific settings
    broker_transport_options={
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True
    },
    
    # Result backend settings  
    result_backend_transport_options={
        'retry_on_timeout': True,
        'retry_on_database_errors': True,
    },
)

# PERIODIC TASK SCHEDULE (Celery Beat) - FIXED
app.conf.beat_schedule = {
    # Weekly email digest - Every Monday at 9:00 AM
    'send-weekly-digest': {
        'task': 'apps.notifications.tasks.send_weekly_digest_to_all_users',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),
        'options': {'queue': 'notifications'}
    },
    
    # Daily popularity metrics update - Every day at 1:00 AM  
    'update-daily-metrics': {
        'task': 'analytics.tasks.update_daily_popularity_metrics',
        'schedule': crontab(hour=1, minute=0),
        'options': {'queue': 'analytics'}
    },
    
    # Generate user recommendations - Every day at 3:00 AM
    'generate-daily-recommendations': {
        'task': 'movies.tasks.generate_recommendations_for_all_users',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'recommendations'}
    },
    
    # Update movie data from external APIs - Every 6 hours
    'update-movie-data': {
        'task': 'movies.tasks.update_movie_database',
        'schedule': crontab(minute=0, hour='*/6'),
        'options': {'queue': 'recommendations'}
    },
    
    # Analytics cleanup - Every Sunday at 2:00 AM
    'cleanup-old-analytics': {
        'task': 'analytics.tasks.cleanup_old_analytics_data',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),
        'options': {'queue': 'analytics'}
    },
    
    # System health check - Every 30 minutes (moved to notifications app)
    'system-health-check': {
        'task': 'apps.notifications.tasks.system_health_check',
        'schedule': crontab(minute='*/30'),
        'options': {'queue': 'notifications'}
    },
    
    # Database maintenance - Every day at 4:00 AM (moved to notifications app)
    'database-maintenance': {
        'task': 'notifications.tasks.database_maintenance',
        'schedule': crontab(hour=4, minute=0),
        'options': {'queue': 'notifications'}
    },
}

# QUEUE CONFIGURATION (SIMPLIFIED - removed default queue)
app.conf.task_default_queue = 'notifications'  # Default to notifications queue
app.conf.task_queues = {
    'notifications': {
        'exchange': 'notifications',
        'routing_key': 'notifications',
    },
    'analytics': {
        'exchange': 'analytics', 
        'routing_key': 'analytics',
    },
    'recommendations': {
        'exchange': 'recommendations',
        'routing_key': 'recommendations',
    },
}

# ERROR HANDLING AND MONITORING
app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# DEVELOPMENT VS PRODUCTION SETTINGS
if os.environ.get('DEBUG', 'False').lower() == 'true':
    # Development settings
    app.conf.task_always_eager = False  # Set to True to run tasks synchronously for testing
    app.conf.task_eager_propagates = True
    app.conf.worker_prefetch_multiplier = 1
else:
    # Production settings
    app.conf.worker_prefetch_multiplier = 4
    app.conf.worker_max_tasks_per_child = 1000  # Restart workers after 1000 tasks
    app.conf.worker_disable_rate_limits = False

# CUSTOM DEBUGGING TASK
@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery functionality"""
    print(f'Request: {self.request!r}')
    return {
        'task_id': self.request.id,
        'task_name': self.request.task,
        'message': 'Celery is working correctly!',
        'worker': self.request.hostname
    }

# STARTUP LOGGING
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Log when periodic tasks are configured"""
    print("✓ Celery periodic tasks configured successfully")
    print("✓ Task queues: notifications, analytics, recommendations")
    print("✓ Background processing ready for movie recommendation system")

# WORKER READY SIGNAL
@app.on_after_finalize.connect  
def setup_queues(sender, **kwargs):
    """Configure additional settings after app is finalized"""
    print("✓ Celery worker configuration finalized")
    print(f"✓ Broker: {app.conf.broker_url}")
    print(f"✓ Result Backend: {app.conf.result_backend}")

# TASK FAILURE HANDLER
@app.task(bind=True)
def handle_task_failure(self, task_id, error, traceback):
    """Handle failed tasks - log and potentially alert"""
    print(f"Task {task_id} failed: {error}")
    # Could send notification to admins here
    return f"Handled failure for task {task_id}"