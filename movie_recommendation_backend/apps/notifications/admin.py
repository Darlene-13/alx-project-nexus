from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from .models import NotificationsPreferences, NotificationLog, InAppNotifications


@admin.register(NotificationsPreferences)
class NotificationsPreferencesAdmin(admin.ModelAdmin):
    """
    Admin interface for notification preferences.
    
    Design decisions:
    - Grouped fields logically for better UX
    - Added search by username for quick user lookup
    - Made user field link to user admin for easy navigation
    - Added custom methods to show preference summaries
    """
    
    list_display = [
        'user_link', 'email_notifications_summary', 'push_notifications_summary',
        'in_app_notifications_summary', 'digest_schedule', 'updated_at'
    ]
    list_filter = [
        'weekly_digest', 'recommendation_alerts', 'trending_alerts',
        'push_recommendations', 'push_trending', 'digest_day', 'timezone'
    ]
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Email Notifications', {
            'fields': ('weekly_digest', 'recommendation_alerts', 'trending_alerts'),
            'description': 'Configure email notification preferences'
        }),
        ('Push Notifications', {
            'fields': ('push_recommendations', 'push_trending'),
            'description': 'Configure push notification preferences'
        }),
        ('In-App Notifications', {
            'fields': ('in_app_recommendations', 'in_app_system_updates'),
            'description': 'Configure in-app notification preferences'
        }),
        ('Timing & Schedule', {
            'fields': ('digest_day', 'digest_time', 'timezone'),
            'description': 'Configure when to send digest notifications'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_link(self, obj):
        """
        Create clickable link to user admin page
        
        Reasoning: Quick navigation to user details without opening new tabs
        """
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def email_notifications_summary(self, obj):
        """
        Show summary of enabled email notifications
        
        Reasoning: Quick overview without expanding each record
        """
        enabled = []
        if obj.weekly_digest:
            enabled.append('Digest')
        if obj.recommendation_alerts:
            enabled.append('Recommendations')
        if obj.trending_alerts:
            enabled.append('Trending')
        
        if enabled:
            return format_html('<span style="color: green;">✓ {}</span>', ', '.join(enabled))
        return format_html('<span style="color: red;">✗ None</span>')
    email_notifications_summary.short_description = 'Email Notifications'
    
    def push_notifications_summary(self, obj):
        """Show summary of enabled push notifications"""
        enabled = []
        if obj.push_recommendations:
            enabled.append('Recommendations')
        if obj.push_trending:
            enabled.append('Trending')
        
        if enabled:
            return format_html('<span style="color: green;">✓ {}</span>', ', '.join(enabled))
        return format_html('<span style="color: red;">✗ None</span>')
    push_notifications_summary.short_description = 'Push Notifications'
    
    def in_app_notifications_summary(self, obj):
        """Show summary of enabled in-app notifications"""
        enabled = []
        if obj.in_app_recommendations:
            enabled.append('Recommendations')
        if obj.in_app_system_updates:
            enabled.append('System Updates')
        
        if enabled:
            return format_html('<span style="color: green;">✓ {}</span>', ', '.join(enabled))
        return format_html('<span style="color: red;">✗ None</span>')
    in_app_notifications_summary.short_description = 'In-App Notifications'
    
    def digest_schedule(self, obj):
        """Show digest schedule in human readable format"""
        day_name = dict(obj.WEEKDAY_CHOICES)[obj.digest_day]
        return f"{day_name} at {obj.digest_time.strftime('%H:%M')} ({obj.timezone})"
    digest_schedule.short_description = 'Digest Schedule'
    
    actions = ['enable_all_notifications', 'disable_all_notifications']
    
    def enable_all_notifications(self, request, queryset):
        """Bulk action to enable all notification types"""
        updated = queryset.update(
            weekly_digest=True,
            recommendation_alerts=True,
            trending_alerts=True,
            push_recommendations=True,
            push_trending=True,
            in_app_recommendations=True,
            in_app_system_updates=True
        )
        self.message_user(request, f'{updated} users had all notifications enabled.')
    enable_all_notifications.short_description = "Enable all notifications for selected users"
    
    def disable_all_notifications(self, request, queryset):
        """Bulk action to disable all notification types"""
        updated = queryset.update(
            weekly_digest=False,
            recommendation_alerts=False,
            trending_alerts=False,
            push_recommendations=False,
            push_trending=False,
            in_app_recommendations=False,
            in_app_system_updates=False
        )
        self.message_user(request, f'{updated} users had all notifications disabled.')
    disable_all_notifications.short_description = "Disable all notifications for selected users"


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """
    Admin interface for notification logs.
    
    Design decisions:
    - Focused on monitoring and analytics
    - Added status-based filtering and coloring
    - Made most fields read-only since logs shouldn't be edited
    - Added bulk actions for status updates
    """
    
    list_display = [
        'id', 'user_link', 'notification_type', 'status_display', 
        'recipient', 'sent_at', 'delivery_metrics', 'engagement_display'
    ]
    list_filter = [
        'status', 'notification_type', 'sent_at', 'delivered_at',
        ('user', admin.RelatedFieldListFilter)
    ]
    search_fields = [
        'user__username', 'notification_type', 'subject', 
        'recipient', 'external_id'
    ]
    readonly_fields = [
        'user', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at', 
        'created_at', 'delivery_time_display', 'engagement_level'
    ]
    date_hierarchy = 'sent_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'subject', 'content')
        }),
        ('Delivery Information', {
            'fields': ('recipient', 'status', 'external_id')
        }),
        ('Timestamps & Metrics', {
            'fields': (
                'sent_at', 'delivered_at', 'opened_at', 'clicked_at', 
                'created_at', 'delivery_time_display', 'engagement_level'
            )
        })
    )
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def status_display(self, obj):
        """
        Color-coded status display
        
        Reasoning: Visual indicators help quickly identify issues
        """
        colors = {
            'sent': '#007cba',      # Blue
            'delivered': '#28a745',  # Green
            'opened': '#17a2b8',     # Teal
            'clicked': '#6f42c1',    # Purple
            'failed': '#dc3545',     # Red
            'scheduled': '#ffc107'   # Yellow
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def delivery_metrics(self, obj):
        """Show delivery timing metrics"""
        if obj.delivery_time:
            seconds = obj.delivery_time.total_seconds()
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h"
        return "N/A"
    delivery_metrics.short_description = 'Delivery Time'
    
    def engagement_display(self, obj):
        """Show engagement level with visual indicators"""
        level_colors = {
            'high': '#28a745',    # Green
            'medium': '#ffc107',  # Yellow
            'low': '#17a2b8',     # Teal
            'none': '#6c757d'     # Gray
        }
        level = obj.engagement_level
        color = level_colors.get(level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, level.title()
        )
    engagement_display.short_description = 'Engagement'
    
    def delivery_time_display(self, obj):
        """Human readable delivery time for detail view"""
        if obj.delivery_time:
            return str(obj.delivery_time)
        return "Not delivered"
    delivery_time_display.short_description = 'Delivery Time'
    
    # Bulk actions for status updates
    actions = ['mark_as_delivered', 'mark_as_failed', 'resend_notifications']
    
    def mark_as_delivered(self, request, queryset):
        """Bulk mark notifications as delivered"""
        updated = queryset.filter(status='sent').update(
            status='delivered',
            delivered_at=timezone.now()
        )
        self.message_user(request, f'{updated} notifications marked as delivered.')
    mark_as_delivered.short_description = "Mark selected as delivered"
    
    def mark_as_failed(self, request, queryset):
        """Bulk mark notifications as failed"""
        updated = queryset.filter(status__in=['sent', 'scheduled']).update(
            status='failed'
        )
        self.message_user(request, f'{updated} notifications marked as failed.')
    mark_as_failed.short_description = "Mark selected as failed"


class InAppNotificationsInline(admin.TabularInline):
    """
    Inline admin for in-app notifications when viewing user details
    
    Design decision: Allow admins to see user's notifications when viewing user profile
    """
    model = InAppNotifications
    extra = 0
    readonly_fields = ['created_at', 'read_at']
    fields = ['category', 'title', 'is_read', 'is_archived', 'created_at']


@admin.register(InAppNotifications)
class InAppNotificationsAdmin(admin.ModelAdmin):
    """
    Admin interface for in-app notifications.
    
    Design decisions:
    - Focused on content management and user engagement
    - Added bulk actions for common operations
    - Visual indicators for read/unread status
    """
    
    list_display = [
        'id', 'user_link', 'title_preview', 'category', 'status_display',
        'created_at', 'expires_at', 'is_expired_display'
    ]
    list_filter = [
        'category', 'is_read', 'is_archived', 'created_at', 'expires_at',
        ('user', admin.RelatedFieldListFilter)
    ]
    search_fields = ['user__username', 'title', 'content', 'category']
    readonly_fields = ['created_at', 'read_at', 'is_expired']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Notification Content', {
            'fields': ('user', 'category', 'title', 'content')
        }),
        ('Actions & Metadata', {
            'fields': ('action_url', 'action_data')
        }),
        ('Status & Timing', {
            'fields': ('is_read', 'is_archived', 'expires_at', 'is_expired')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def title_preview(self, obj):
        """
        Show truncated title with full title in tooltip
        
        Reasoning: Keep list view compact while allowing full title access
        """
        title = obj.title if hasattr(obj, 'title') else 'No Title'
        if len(title) > 50:
            return format_html(
                '<span title="{}">{}</span>',
                title, title[:47] + '...'
            )
        return title
    title_preview.short_description = 'Title'
    
    def status_display(self, obj):
        """Visual status display with icons"""
        if obj.is_archived:
            return format_html('<span style="color: #6c757d;">📁 Archived</span>')
        elif obj.is_read:
            return format_html('<span style="color: #28a745;">✓ Read</span>')
        else:
            return format_html('<span style="color: #007cba; font-weight: bold;">📧 Unread</span>')
    status_display.short_description = 'Status'
    
    def is_expired_display(self, obj):
        """Show expiration status with visual indicators"""
        if obj.is_expired:
            return format_html('<span style="color: #dc3545;">⚠️ Expired</span>')
        elif obj.expires_at:
            return format_html('<span style="color: #ffc107;">⏰ Expires Soon</span>')
        return format_html('<span style="color: #28a745;">✓ Active</span>')
    is_expired_display.short_description = 'Expiration Status'
    
    # Bulk actions
    actions = [
        'mark_as_read', 'mark_as_unread', 'archive_notifications',
        'delete_expired', 'extend_expiration'
    ]
    
    def mark_as_read(self, request, queryset):
        """Bulk mark notifications as read"""
        updated = 0
        for notification in queryset.filter(is_read=False):
            notification.mark_as_read()
            updated += 1
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark selected as read"
    
    def mark_as_unread(self, request, queryset):
        """Bulk mark notifications as unread"""
        updated = queryset.filter(is_read=True).update(
            is_read=False,
            read_at=None
        )
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = "Mark selected as unread"
    
    def archive_notifications(self, request, queryset):
        """Bulk archive notifications"""
        updated = 0
        for notification in queryset.filter(is_archived=False):
            notification.archive()
            updated += 1
        self.message_user(request, f'{updated} notifications archived.')
    archive_notifications.short_description = "Archive selected notifications"
    
    def delete_expired(self, request, queryset):
        """Delete expired notifications"""
        expired_count = 0
        for notification in queryset:
            if notification.is_expired:
                notification.delete()
                expired_count += 1
        self.message_user(request, f'{expired_count} expired notifications deleted.')
    delete_expired.short_description = "Delete expired notifications"
    
    def extend_expiration(self, request, queryset):
        """Extend expiration by 30 days"""
        from datetime import timedelta
        updated = queryset.filter(expires_at__isnull=False).update(
            expires_at=timezone.now() + timedelta(days=30)
        )
        self.message_user(request, f'{updated} notifications had expiration extended by 30 days.')
    extend_expiration.short_description = "Extend expiration by 30 days"


# Custom admin site configuration
admin.site.site_header = "Movie Recommendations - Notifications Admin"
admin.site.site_title = "Notifications Admin"
admin.site.index_title = "Notification Management"