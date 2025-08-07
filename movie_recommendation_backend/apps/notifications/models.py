from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

User = get_user_model()

class NotificationsPreferences(models.Model):
    """
    This is the user preference model for email or push notifications.
    It stores comprehensive notification settings for each user.
    """

    # Weekday choices for notification preferences
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    # Core field
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences', unique=True)
    # Email Notification Preferences
    weekly_digest = models.BooleanField(default=False, help_text="Receive a weekly digest of notifications" )
    recommendation_alerts = models.BooleanField(default=False, help_text="Receive alerts for new movie recommendations")
    trending_alerts = models.BooleanField(default=False, help_text="Receive alerts for trending movies")
    # Push notifications preferences
    push_recommendations = models.BooleanField(default=False, help_text="Receive push notifications for new recommendations")
    push_trending = models.BooleanField(default=False, help_text="Receive push notifications for trending movies")
    #In-App Notifications and Preferences
    in_app_recommendations = models.BooleanField(default=False, help_text="Receive in-app notifications for new recommendations")
    in_app_sysem_updates = models.BooleanField(default=False, help_text="Receive in-app notifications for system updates")
    #Timing prefereces
    digest_day = models.IntegerField(choices=WEEKDAY_CHOICES, default=0, help_text="Day of the week to receive the weekly digest")
    digest_time = models.TimeField(default=timezone.now, help_text="Time of day to receive the weekly digest")

    # Core field
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences', unique=True)
    # Email Notification Preferences
    weekly_digest = models.BooleanField(default=False, help_text="Receive a weekly digest of notifications" )
    recommendation_alerts = models.BooleanField(default=False, help_text="Receive alerts for new movie recommendations")
    trending_alerts = models.BooleanField(default=False, help_text="Receive alerts for trending movies")
    # Push notifications preferences
    push_recommendations = models.BooleanField(default=False, help_text="Receive push notifications for new recommendations")
    push_trending = models.BooleanField(default=False, help_text="Receive push notifications for trending movies")
    #In-App Notifications and Preferences
    in_app_recommendations = models.BooleanField(default=False, help_text="Receive in-app notifications for new recommendations")
    in_app_system_updates = models.BooleanField(default=False, validators=[MinValueValidator(0), MaxValueValidator(6)], help_text="Receive in-app notifications for system updates")
    #Timing preferences
    digest_day = models.IntegerField(choices=WEEKDAY_CHOICES, default=0, help_text="Day of the week to receive the weekly digest")
    digest_time = models.TimeField(default=timezone.now, help_text="Time of day to receive the weekly digest")
    timezone = models.CharField(max_length=50, default='UTC', help_text="User's timezone for scheduling notifications")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the preferences were created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the preferences were last updated")

    class Meta:
        db_table = 'notifications_preferences'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

        indexes = [
            models.Index(fields=['user'], name='idx_notifprefs_user'),
            models.Index(fields=['digest_day', 'digest_time'], name='idx_notifprefs_digest'),
        ]

    def __str__(self):
        return f"Notification preferences for {self.user.username}"
    
    @property
    def has_email_notifications(self):
        """ Check if the user has enabled any email notifications."""
        return any([
            self.in_app_recommendations,
            self.in_app_system_updates
        ])
    
class NotificationLog(models.Model):
    """
    This model logs the notifications that has been sent to the users.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_logs')
    notification_type = models.CharField(max_length=50, help_text="Type of notification sent")
    subject = models.CharField(max_length=255, help_text="Subject of the notification")
    content = models.TextField(help_text="Content of the notification")
    recipient = models.CharField(max_length=255, help_text="Email address or device token of the recipient")
    status = models.CharField(max_length=50, choices=[
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('clicked', 'Clicked'),
        ('opened', 'Opened'),
        ('delivered', 'Delivered'),
        ('scheduled', 'Scheduled'),
    ], default='sent', help_text="Status of the notification")
    external_id = models.CharField(max_length=255, null=True, unique=True, help_text="Unique identifier for the notification")
    sent_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the notification was sent")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the notification was delivered")
    opened_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the notification was opened")
    clicked_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the notification was clicked") 
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the log entry was created")
    
    class Meta:
        db_table = 'notification_logs'
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        indexes = [
            models.Index(fields=['user', 'notification_type'], name='idx_notif_log_user_type'),
            models.Index(fields=['status'], name='idx_notif_log_status'),
            models.Index(fields=['notification_type', 'sent_at'], name='idx_notif_log_type_sent'),
            models.Index(fields=['created_at'], name='idx_notif_log_created_at')
        ]
    ordering = ['-created_at']

    def __str__(self):
        return f"Notification Log for {self.user_id.username} - {self.notification_type} - {self.status} - {self.sent_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def mark_as_sent(self):
        self.status = 'sent'
        self.sent_at = timezone.now()
        if self.external_id:
            self.external_id = self.external_id
        self.save(update_fields=['status', 'sent_at','external_id', 'updated_at'])

    def mark_as_delivered(self):
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        if self.external_id:
            self.external_id = self.external_id
        self.save(update_fields=['status', 'delivered_at', 'external_id', 'updated_at'])

    def mark_as_failed(self):
        self.status = 'failed'
        self.failed_at = timezone.now()
        if self.external_id:
            self.external_id = self.external_id
        self.save(update_fields=['status', 'failed_at', 'external_id', 'updated_at'])
    def mark_as_clicked(self):
        self.status = 'clicked'
        self.clicked_at = timezone.now()
        if self.external_id:
            self.external_id = self.external_id
        self.save(update_fields=['status', 'clicked_at', 'external_id', 'updated_at'])

    def mark_as_opened(self):
        self.status = 'opened'
        self.opened_at = timezone.now()
        if self.external_id:
            self.external_id = self.external_id
        self.save(update_fields=['status', 'opened_at', 'external_id', 'updated_at'])

    def mark_as_scheduled(self):
        self.status = 'scheduled'
        self.scheduled_at = timezone.now()
        if self.external_id:
            self.external_id = self.external_id
        self.save(update_fields=['status', 'scheduled_at', 'external_id', 'updated_at'])

    @property
    def delivery_time(self):
        """
        Calculate the time between creation and delivery
        """
        if self.delivered_at:
            return self.delivered_at - self.created_at
        return None
    
    @property
    def is_successful(self):
        """
        Check if the notification was successfully delivered
        """
        if self.status == "delivered":
            return self.status in ["delivered", "opened", "clicked"]
        return False
    
    @property
    def engagement_level(self):
        if self.clicked_at:
            return 'high'
        if self.opened_at:
            return 'medium'
        if self.delivered_at:
            return 'low'
        else:
            return 'none'
        
class InAppNotifications(models.Model):
    """
    This is an additional model for our In apps notifications for easier querying and filtering.
    """
    NOTIFICATION_PREFERENCES = [
        ('recommendation','New Recommendation'),
        ('system','System Notification'),
        ('social','Social'),
        ('promotion','Promotion'),
        ('announcement','Annoucement')
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='in_app_notifications')
    category = models.CharField(choices=NOTIFICATION_PREFERENCES, default='system', max_length=50)
    title = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    #Metadata
    action_url = models.URLField(null=True, blank=True, help_text="URL to redirect when notification is clicked")
    action_data = models.JSONField(null=True, blank=True, help_text="Additional data for notification actions")
    # status
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    #Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this notification should automatically be archived")

    class Meta:
        db_table = "in_app_notifications"
        verbose_name = 'In_App_Notification'
        verbose_name_plural = 'In_App_Notifications'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_in_app_user_created'),
            models.Index(fields=['user', 'is_read'], name='idx_in_app_user_read'),
            models.Index(fields=['expires_at'], name='idx_in_app_expires'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"In-app notification for {self.user.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def archive(self):
        """Archive the notification"""
        self.is_archived = True
        self.save(update_fields=['is_archived'])
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
