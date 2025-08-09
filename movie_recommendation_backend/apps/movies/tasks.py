from celery import shared_task
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def generate_recommendations_for_user(user_id, limit=10):
    """Generate personalized recommendations for a user"""
    try:
        user = User.objects.get(id=user_id)
        
        # Your recommendation algorithm here
        # This is a placeholder
        from movies.models import Movie
        recommendations = Movie.objects.filter(is_active=True).order_by('-average_rating')[:limit]
        
        recommendation_data = []
        for movie in recommendations:
            recommendation_data.append({
                'movie_id': movie.id,
                'title': movie.title,
                'score': float(getattr(movie, 'average_rating', 0))
            })
        
        return {'success': True, 'user_id': user_id, 'recommendations': recommendation_data}
    except Exception as exc:
        return {'success': False, 'error': str(exc)}

@shared_task
def generate_recommendations_for_all_users():
    """Generate recommendations for all active users"""
    users = User.objects.filter(is_active=True)
    successful = 0
    
    for user in users:
        try:
            generate_recommendations_for_user.delay(user.id)
            successful += 1
        except Exception as e:
            logger.error(f"Failed to queue recommendations for user {user.id}: {e}")
    
    return {'success': True, 'queued_users': successful}

@shared_task  
def update_movie_database():
    """Update movie data from external APIs"""
    try:
        # Placeholder for API integration
        # Example: fetch from TMDB, OMDB, etc.
        
        updated_movies = 0
        # Your API integration logic here
        
        return {'success': True, 'updated_movies': updated_movies}
    except Exception as exc:
        return {'success': False, 'error': str(exc)}