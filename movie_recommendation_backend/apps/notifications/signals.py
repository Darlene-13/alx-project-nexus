from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging

from .models import NotificationsPreferences, NotificationLog, InAppNotifications

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """
    Automatically create notification preferences for new users.
    This ensures every user has default notification settings.
    """
    if created:
        try:
            # Create default notification preferences
            NotificationsPreferences.objects.create(
                user=instance,
                # Default settings - can be customized based on user type or registration source
                weekly_digest=True,
                recommendation_alerts=True,
                trending_alerts=False,
                push_recommendations=True,
                push_trending=False,
                in_app_recommendations=True,
                in_app_system_updates=True,
                digest_day=1,  # Monday
                digest_time='09:00:00',
                timezone=getattr(settings, 'TIME_ZONE', 'UTC')
            )
            
            # Create welcome in-app notification
            InAppNotifications.objects.create(
                user=instance,
                category='system',
                title='Welcome to Movie Recommendations!',
                message=f'Hi {instance.first_name or instance.username}! '
                       'Welcome to our movie recommendation platform. '
                       'Explore personalized movie suggestions tailored just for you.',
                action_url='/dashboard/',
                expires_at=timezone.now() + timezone.timedelta(days=30)
            )
            
            logger.info(f"Created notification preferences for user: {instance.username}")
            
        except Exception as e:
            logger.error(f"Failed to create notification preferences for user {instance.username}: {str(e)}")


@receiver(post_save, sender=NotificationsPreferences)
def invalidate_user_preferences_cache(sender, instance, **kwargs):
    """
    Invalidate cached user preferences when they are updated.
    This ensures notification services get fresh preference data.
    """
    cache_key = f"notification_preferences_{instance.user.id}"
    cache.delete(cache_key)
    
    # Also invalidate user's notification-related cache keys
    cache.delete(f"user_digest_enabled_{instance.user.id}")
    cache.delete(f"user_push_enabled_{instance.user.id}")
    cache.delete(f"user_email_enabled_{instance.user.id}")
    
    logger.debug(f"Invalidated notification preferences cache for user: {instance.user.username}")


@receiver(post_save, sender=NotificationLog)
def update_notification_metrics(sender, instance, created, **kwargs):
    """
    Update real-time notification metrics when logs are created or updated.
    This helps with monitoring and analytics.
    """
    if created:
        # Increment counters for new notifications
        cache_key_total = f"notifications_total_{instance.notification_type}"
        cache_key_daily = f"notifications_daily_{timezone.now().date()}_{instance.notification_type}"
        
        # Increment with expiry
        current_total = cache.get(cache_key_total, 0)
        cache.set(cache_key_total, current_total + 1, timeout=86400)  # 24 hours
        
        current_daily = cache.get(cache_key_daily, 0)
        cache.set(cache_key_daily, current_daily + 1, timeout=86400)  # 24 hours
        
    # Update success rate counters when status changes
    if instance.status in ['delivered', 'opened', 'clicked']:
        cache_key_success = f"notifications_success_{instance.notification_type}"
        current_success = cache.get(cache_key_success, 0)
        cache.set(cache_key_success, current_success + 1, timeout=86400)


@receiver(pre_save, sender=NotificationLog)
def track_notification_status_changes(sender, instance, **kwargs):
    """
    Track when notification status changes and log important transitions.
    This helps with debugging delivery issues.
    """
    if instance.pk:  # Only for existing objects
        try:
            old_instance = NotificationLog.objects.get(pk=instance.pk)
            
            # Log status changes
            if old_instance.status != instance.status:
                logger.info(
                    f"Notification {instance.id} status changed: "
                    f"{old_instance.status} -> {instance.status} "
                    f"(User: {instance.user.username}, Type: {instance.notification_type})"
                )
                
                # Special handling for failures
                if instance.status == 'failed' and old_instance.status != 'failed':
                    logger.warning(
                        f"Notification {instance.id} failed for user {instance.user.username}. "
                        f"Error: {instance.error_message}"
                    )
                    
                    # Create in-app notification for critical failures (optional)
                    if instance.priority in ['high', 'urgent']:
                        InAppNotifications.objects.create(
                            user=instance.user,
                            category='system',
                            title='Notification Delivery Issue',
                            message='We had trouble delivering an important notification to you. '
                                   'Please check your notification settings.',
                            action_url='/settings/notifications/',
                            expires_at=timezone.now() + timezone.timedelta(days=7)
                        )
                
        except NotificationLog.DoesNotExist:
            pass  # New object, no previous state to compare


@receiver(post_save, sender=InAppNotifications)
def update_unread_notification_count(sender, instance, created, **kwargs):
    """
    Update user's unread notification count cache when in-app notifications change.
    """
    if created or (hasattr(instance, '_state') and 'is_read' in instance._state.fields_cache):
        # Calculate new unread count
        unread_count = InAppNotifications.objects.filter(
            user=instance.user,
            is_read=False,
            is_archived=False
        ).count()
        
        # Update cache
        cache_key = f"unread_notifications_{instance.user.id}"
        cache.set(cache_key, unread_count, timeout=3600)  # 1 hour
        
        logger.debug(f"Updated unread notification count for user {instance.user.username}: {unread_count}")


@receiver(post_delete, sender=InAppNotifications)
def update_unread_count_on_delete(sender, instance, **kwargs):
    """
    Update unread count when in-app notifications are deleted.
    """
    if not instance.is_read:
        unread_count = InAppNotifications.objects.filter(
            user=instance.user,
            is_read=False,
            is_archived=False
        ).count()
        
        cache_key = f"unread_notifications_{instance.user.id}"
        cache.set(cache_key, unread_count, timeout=3600)


# Utility functions for working with signals

def get_user_notification_preferences(user_id):
    """
    Get user notification preferences with caching.
    Used by notification services to check user preferences efficiently.
    """
    cache_key = f"notification_preferences_{user_id}"
    preferences = cache.get(cache_key)
    
    if preferences is None:
        try:
            preferences = NotificationsPreferences.objects.get(user_id=user_id)
            cache.set(cache_key, preferences, timeout=3600)  # 1 hour
        except NotificationsPreferences.DoesNotExist:
            # Create default preferences if they don't exist
            user = User.objects.get(id=user_id)
            preferences = NotificationsPreferences.objects.create(user=user)
            cache.set(cache_key, preferences, timeout=3600)
    
    return preferences


def get_unread_notification_count(user_id):
    """
    Get user's unread notification count with caching.
    """
    cache_key = f"unread_notifications_{user_id}"
    count = cache.get(cache_key)
    
    if count is None:
        count = InAppNotifications.objects.filter(
            user_id=user_id,
            is_read=False,
            is_archived=False
        ).count()
        cache.set(cache_key, count, timeout=3600)  # 1 hour
    
    return count


def mark_all_notifications_read(user_id):
    """
    Mark all unread notifications as read for a user.
    """
    updated_count = InAppNotifications.objects.filter(
        user_id=user_id,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    # Clear the unread count cache
    cache_key = f"unread_notifications_{user_id}"
    cache.set(cache_key, 0, timeout=3600)
    
    return updated_count


def cleanup_expired_notifications():
    """
    Utility function to clean up expired in-app notifications.
    Should be called by a periodic task (Celery beat).
    """
    now = timezone.now()
    expired_count = InAppNotifications.objects.filter(
        expires_at__lt=now,
        is_archived=False
    ).update(is_archived=True)
    
    logger.info(f"Archived {expired_count} expired in-app notifications")
    return expired_count


def get_notification_analytics(days=30):
    """
    Get notification analytics for the specified number of days.
    Used by admin dashboard and reporting.
    """
    from datetime import timedelta
    from django.db.models import Count, Q
    
    start_date = timezone.now() - timedelta(days=days)
    
    analytics = {
        'total_sent': NotificationLog.objects.filter(created_at__gte=start_date).count(),
        'by_type': NotificationLog.objects.filter(
            created_at__gte=start_date
        ).values('notification_type').annotate(
            count=Count('id'),
            success_rate=Count('id', filter=Q(status__in=['delivered', 'opened', 'clicked'])) * 100.0 / Count('id')
        ),
        'by_status': NotificationLog.objects.filter(
            created_at__gte=start_date
        ).values('status').annotate(count=Count('id')),
        'engagement_metrics': {
            'opened': NotificationLog.objects.filter(
                created_at__gte=start_date,
                status__in=['opened', 'clicked']
            ).count(),
            'clicked': NotificationLog.objects.filter(
                created_at__gte=start_date,
                status='clicked'
            ).count(),
        }
    }
    
    return analytics