from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import NotificationsPreferences, NotificationLog, InAppNotifications

User = get_user_model()


class NotificationsPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for user notification preferences.
    
    Design decisions:
    - Made user field read-only since preferences are tied to authenticated user
    - Added validation for digest_time to ensure it's a reasonable time
    - Created separate fields for better API usability
    """
    
    # Read-only fields that shouldn't be modified via API
    user = serializers.StringRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Custom field to get user's display name
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = NotificationsPreferences
        fields = [
            'id', 'user', 'username',
            # Email preferences
            'weekly_digest', 'recommendation_alerts', 'trending_alerts',
            # Push preferences  
            'push_recommendations', 'push_trending',
            # In-app preferences
            'in_app_recommendations', 'in_app_system_updates',
            # Timing
            'digest_day', 'digest_time', 'timezone',
            # Timestamps
            'created_at', 'updated_at'
        ]
    
    def validate_digest_time(self, value):
        """
        Validate that digest_time is within reasonable hours (6 AM to 11 PM)
        
        Reasoning: Prevent users from setting digest times at unreasonable hours
        like 3 AM which might indicate a mistake in timezone handling
        """
        if value.hour < 6 or value.hour > 23:
            raise serializers.ValidationError(
                "Digest time should be between 6:00 AM and 11:00 PM"
            )
        return value
    
    def validate_timezone(self, value):
        """
        Validate timezone string against common timezone formats
        
        Reasoning: Ensure timezone is valid to prevent scheduling errors
        """
        import pytz
        try:
            pytz.timezone(value)
        except pytz.exceptions.UnknownTimeZoneError:
            raise serializers.ValidationError(f"Invalid timezone: {value}")
        return value


class NotificationsPreferencesUpdateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for updating preferences.
    
    Design decision: Separate serializer for updates to avoid exposing
    unnecessary fields and to have cleaner validation
    """
    
    class Meta:
        model = NotificationsPreferences
        fields = [
            'weekly_digest', 'recommendation_alerts', 'trending_alerts',
            'push_recommendations', 'push_trending',
            'in_app_recommendations', 'in_app_system_updates',
            'digest_day', 'digest_time', 'timezone'
        ]


class NotificationLogSerializer(serializers.ModelSerializer):
    """
    Serializer for notification logs.
    
    Design decisions:
    - Made most fields read-only since logs shouldn't be modified
    - Added computed fields for better API usability
    - Included user details for admin views
    """
    
    user_details = serializers.SerializerMethodField()
    delivery_time_seconds = serializers.SerializerMethodField()
    engagement_level = serializers.CharField(read_only=True)
    is_successful = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'user', 'user_details', 'notification_type', 
            'subject', 'content', 'recipient', 'status', 'external_id',
            'sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'created_at',
            'delivery_time_seconds', 'engagement_level', 'is_successful'
        ]
        read_only_fields = [
            'sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'created_at'
        ]
    
    def get_user_details(self, obj):
        """
        Return user details for easier consumption by frontend
        
        Reasoning: Avoid additional API calls to get user info
        """
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': getattr(obj.user, 'email', None)
        }
    
    def get_delivery_time_seconds(self, obj):
        """
        Return delivery time in seconds for easier processing
        
        Reasoning: Frontend often needs numeric values for charts/analytics
        """
        delivery_time = obj.delivery_time
        return delivery_time.total_seconds() if delivery_time else None


class NotificationLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating notification logs.
    
    Design decision: Separate create serializer to control what fields
    can be set during creation vs. what gets updated by system processes
    """
    
    class Meta:
        model = NotificationLog
        fields = [
            'user', 'notification_type', 'subject', 'content', 
            'recipient', 'external_id'
        ]
    
    def create(self, validated_data):
        """
        Override create to set initial status
        
        Reasoning: New notifications should start with 'scheduled' status
        """
        validated_data['status'] = 'scheduled'
        return super().create(validated_data)


class InAppNotificationsSerializer(serializers.ModelSerializer):
    """
    Serializer for in-app notifications.
    
    Design decisions:
    - Made user read-only (set from authenticated user)
    - Added computed fields for frontend convenience
    - Separate actions for state changes (read, archive)
    """
    
    user = serializers.StringRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    time_since_created = serializers.SerializerMethodField()
    
    class Meta:
        model = InAppNotifications
        fields = [
            'id', 'user', 'username', 'category', 'title', 'content',
            'action_url', 'action_data', 'is_read', 'is_archived',
            'created_at', 'read_at', 'expires_at', 'is_expired',
            'time_since_created'
        ]
        read_only_fields = ['created_at', 'read_at']
    
    def get_time_since_created(self, obj):
        """
        Return human-readable time since creation
        
        Reasoning: Frontend often needs relative time display
        """
        from django.utils.timesince import timesince
        return timesince(obj.created_at)


class InAppNotificationsCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating in-app notifications.
    
    Design decision: Simplified fields for creation, system sets timestamps
    """
    
    class Meta:
        model = InAppNotifications
        fields = [
            'user', 'category', 'title', 'content', 
            'action_url', 'action_data', 'expires_at'
        ]


class InAppNotificationBulkActionSerializer(serializers.Serializer):
    """
    Serializer for bulk actions on in-app notifications.
    
    Design decision: Separate serializer for bulk operations to handle
    multiple notification IDs and action types efficiently
    """
    
    ACTION_CHOICES = [
        ('mark_read', 'Mark as Read'),
        ('mark_unread', 'Mark as Unread'),
        ('archive', 'Archive'),
        ('delete', 'Delete'),
    ]
    
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of notification IDs to perform action on"
    )
    action = serializers.ChoiceField(
        choices=ACTION_CHOICES,
        help_text="Action to perform on selected notifications"
    )
    
    def validate_notification_ids(self, value):
        """
        Validate that all notification IDs exist and belong to the user
        
        Reasoning: Security - prevent users from acting on other users' notifications
        """
        user = self.context['request'].user
        existing_ids = InAppNotifications.objects.filter(
            id__in=value, user=user
        ).values_list('id', flat=True)
        
        if len(existing_ids) != len(value):
            invalid_ids = set(value) - set(existing_ids)
            raise serializers.ValidationError(
                f"Invalid notification IDs: {list(invalid_ids)}"
            )
        return value


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer for notification statistics.
    
    Design decision: Custom serializer for dashboard/analytics data
    that doesn't map to a specific model
    """
    
    total_sent = serializers.IntegerField()
    total_delivered = serializers.IntegerField()
    total_opened = serializers.IntegerField()
    total_clicked = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()
    click_rate = serializers.FloatField()
    avg_delivery_time_seconds = serializers.FloatField()
    
    # Breakdown by notification type
    by_type = serializers.DictField()
    
    # Recent activity
    recent_notifications = NotificationLogSerializer(many=True, read_only=True)