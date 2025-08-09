from celery import shared_task
from django.contrib.auth import get_user_model
from apps.notifications.services import BrevoEmailService
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, max_retries=3)
def send_email_task(self, to_email, subject, template_name, context=None):
    """Background task for sending emails"""
    try:
        email_service = BrevoEmailService()
        result = email_service.send_email(
            to_email=to_email,
            subject=subject,
            template_name=template_name,
            context=context or {}
        )
        return {'success': True, 'email': to_email}
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return {'success': False, 'email': to_email, 'error': str(exc)}

@shared_task
def send_welcome_email_task(user_id):
    """Send welcome email to new user"""
    try:
        user = User.objects.get(id=user_id)
        email_service = BrevoEmailService()
        return email_service.send_welcome_email(user.email, user.first_name or user.username)
    except User.DoesNotExist:
        return {'success': False, 'error': 'User not found'}

@shared_task
def send_weekly_digest_to_all_users():
    """Send weekly digest to all active users"""
    users = User.objects.filter(is_active=True)
    successful = 0
    for user in users:
        try:
            email_service = BrevoEmailService()
            # Get user recommendations (implement this logic)
            recommendations = get_user_recommendations(user)
            email_service.send_recommendation_digest(
                user.email, 
                user.first_name or user.username,
                recommendations
            )
            successful += 1
        except Exception as e:
            logger.error(f"Failed to send digest to {user.email}: {e}")
    return {'success': True, 'sent_count': successful}

def get_user_recommendations(user, limit=5):
    """Helper to get recommendations for user"""
    # Placeholder - implement your recommendation logic
    return []