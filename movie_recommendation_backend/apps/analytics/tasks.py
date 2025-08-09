from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def log_user_activity_task(user_id, action_type, session_id, ip_address, user_agent, source, movie_id=None, referer=None, metadata=None):
    """Background task for logging user activity"""
    try:
        from analytics.models import UserActivityLog
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.get(id=user_id) if user_id else None
        
        activity = UserActivityLog.log_activity(
            action_type=action_type,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            source=source,
            User=user,
            referer=referer,
            metadata=metadata
        )
        return {'success': True, 'activity_id': activity.id}
    except Exception as exc:
        logger.error(f"Failed to log activity: {exc}")
        return {'success': False, 'error': str(exc)}

@shared_task
def update_daily_popularity_metrics(date=None):
    """Update daily popularity metrics for all movies"""
    try:
        from analytics.models import PopularityMetrics
        from movies.models import Movie
        
        if date is None:
            date = timezone.now().date()
        
        movies = Movie.objects.all()
        updated_count = 0
        
        for movie in movies:
            try:
                PopularityMetrics.update_daily_metrics(movie, date)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update metrics for movie {movie.id}: {e}")
        
        return {'success': True, 'updated_movies': updated_count, 'date': str(date)}
    except Exception as exc:
        logger.error(f"Failed to update daily metrics: {exc}")
        return {'success': False, 'error': str(exc)}

@shared_task
def cleanup_old_analytics_data(days_to_keep=90):
    """Clean up old analytics data"""
    try:
        from analytics.models import UserActivityLog
        
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        deleted_count, _ = UserActivityLog.objects.filter(timestamp__lt=cutoff_date).delete()
        
        return {'success': True, 'deleted_records': deleted_count}
    except Exception as exc:
        return {'success': False, 'error': str(exc)}
