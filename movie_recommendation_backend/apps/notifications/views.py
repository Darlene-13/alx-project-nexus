from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from datetime import timedelta

from .models import NotificationsPreferences, NotificationLog, InAppNotifications
from .serializers import (
    NotificationsPreferencesSerializer,
    NotificationsPreferencesUpdateSerializer,
    NotificationLogSerializer,
    NotificationLogCreateSerializer,
    InAppNotificationsSerializer,
    InAppNotificationsCreateSerializer,
    InAppNotificationBulkActionSerializer,
    NotificationStatsSerializer
)


def notifications_hub(request):
    """
    Notifications app hub showing all available endpoints.
    """

    endpoints = {
        "🔔 NOTIFICATION PREFERENCES": [
            {"method": "GET", "url": "/notifications/api/v1/preferences/", "description": "Get current user's preferences"},
            {"method": "PATCH", "url": "/notifications/api/v1/preferences/{id}/", "description": "Update preferences"},
            {"method": "GET", "url": "/notifications/api/v1/preferences/my_preferences/", "description": "Get my preferences"},
            {"method": "POST", "url": "/notifications/api/v1/preferences/reset_to_defaults/", "description": "Reset to defaults"},
            {"method": "GET", "url": "/notifications/api/v1/preferences/summary/", "description": "Admin summary of all preferences"},
        ],
        "📝 NOTIFICATION LOGS": [
            {"method": "GET", "url": "/notifications/api/v1/logs/", "description": "List notification logs"},
            {"method": "POST", "url": "/notifications/api/v1/logs/", "description": "Create a log (admin only)"},
            {"method": "POST", "url": "/notifications/api/v1/logs/{id}/mark_delivered/", "description": "Mark as delivered"},
            {"method": "POST", "url": "/notifications/api/v1/logs/{id}/mark_opened/", "description": "Mark as opened"},
            {"method": "POST", "url": "/notifications/api/v1/logs/{id}/mark_clicked/", "description": "Mark as clicked"},
            {"method": "GET", "url": "/notifications/api/v1/logs/stats/", "description": "Log statistics"},
            {"method": "GET", "url": "/notifications/api/v1/logs/my_logs/", "description": "Current user's logs"},
        ],
        "📬 IN-APP NOTIFICATIONS": [
            {"method": "GET", "url": "/notifications/api/v1/inapp/", "description": "List in-app notifications"},
            {"method": "POST", "url": "/notifications/api/v1/inapp/", "description": "Create in-app notification"},
            {"method": "POST", "url": "/notifications/api/v1/inapp/{id}/mark_read/", "description": "Mark as read"},
            {"method": "POST", "url": "/notifications/api/v1/inapp/{id}/archive/", "description": "Archive"},
            {"method": "POST", "url": "/notifications/api/v1/inapp/bulk_action/", "description": "Bulk actions"},
            {"method": "GET", "url": "/notifications/api/v1/inapp/unread_count/", "description": "Unread count"},
            {"method": "GET", "url": "/notifications/api/v1/inapp/recent/", "description": "Recent unread"},
            {"method": "POST", "url": "/notifications/api/v1/inapp/mark_all_read/", "description": "Mark all as read"},
            {"method": "DELETE", "url": "/notifications/api/v1/inapp/clear_all/", "description": "Delete all archived"},
            {"method": "GET", "url": "/notifications/api/v1/inapp/categories/", "description": "Get categories with counts"},
        ],
        "🛠 SYSTEM HEALTH": [
            {"method": "GET", "url": "/notifications/api/v1/health/system_health/", "description": "Check system health"},
        ],
        "📘 API DOCUMENTATION": [
            {"method": "GET", "url": "/notifications/docs/", "description": "Swagger UI", "status": "✅ Active"},
            {"method": "GET", "url": "/notifications/redoc/", "description": "ReDoc UI", "status": "✅ Active"},
            {"method": "GET", "url": "/notifications/schema/", "description": "Schema (JSON)", "status": "✅ Active"},
        ]
    }

    return render(request, 'notifications/notifications_hub.html', {
        'app_name': '🔔 Notifications API Hub',
        'app_description': 'Explore and monitor all endpoints in the Notifications system',
        'endpoints': endpoints,
    })

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners or admins to access objects.
    
    Design decision: Reusable permission class to ensure users can only
    access their own notification data while allowing admin full access
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user.is_staff:
            return True
        
        # Object owner has access
        return obj.user == request.user


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for notification-related endpoints.
    
    Design decision: Consistent pagination across all notification endpoints
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationsPreferencesViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notification preferences.
    
    Design decisions:
    - Users can only access their own preferences
    - Auto-create preferences if they don't exist
    - Separate serializers for read/write operations
    - Added action to reset to defaults
    """
    
    serializer_class = NotificationsPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter queryset to current user's preferences only
        
        Reasoning: Users should only see their own preferences
        """
        if self.request.user.is_staff:
            return NotificationsPreferences.objects.all()
        return NotificationsPreferences.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """
        Use different serializers for different actions
        
        Reasoning: Update operations don't need all read-only fields
        """
        if self.action in ['update', 'partial_update']:
            return NotificationsPreferencesUpdateSerializer
        return NotificationsPreferencesSerializer
    
    def get_object(self):
        """
        Get or create preferences for current user
        
        Reasoning: Simplify frontend - always returns preferences object
        """
        if self.request.user.is_staff and 'pk' in self.kwargs:
            # Admin accessing specific user's preferences
            return super().get_object()
        
        # Regular user accessing their own preferences
        preferences, created = NotificationsPreferences.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    def perform_create(self, serializer):
        """Set user to current user when creating"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_preferences(self, request):
        """
        Endpoint to get current user's preferences
        
        Design decision: Explicit endpoint for frontend convenience
        URL: /api/notifications/preferences/my_preferences/
        """
        preferences = self.get_object()
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def reset_to_defaults(self, request):
        """
        Reset user's preferences to default values
        
        Reasoning: Common user request to start fresh
        """
        preferences = self.get_object()
        
        # Reset all preferences to model defaults
        for field in NotificationsPreferences._meta.fields:
            if hasattr(field, 'default') and field.name not in ['id', 'user', 'created_at', 'updated_at']:
                setattr(preferences, field.name, field.default)
        
        preferences.save()
        serializer = self.get_serializer(preferences)
        
        return Response({
            'message': 'Preferences reset to defaults',
            'preferences': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get summary of notification preferences across all users (admin only)
        
        Reasoning: Analytics for admin dashboard
        """
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=403)
        
        total_users = NotificationsPreferences.objects.count()
        
        summary = {
            'total_users': total_users,
            'email_notifications': {
                'weekly_digest': NotificationsPreferences.objects.filter(weekly_digest=True).count(),
                'recommendation_alerts': NotificationsPreferences.objects.filter(recommendation_alerts=True).count(),
                'trending_alerts': NotificationsPreferences.objects.filter(trending_alerts=True).count(),
            },
            'push_notifications': {
                'recommendations': NotificationsPreferences.objects.filter(push_recommendations=True).count(),
                'trending': NotificationsPreferences.objects.filter(push_trending=True).count(),
            },
            'in_app_notifications': {
                'recommendations': NotificationsPreferences.objects.filter(in_app_recommendations=True).count(),
                'system_updates': NotificationsPreferences.objects.filter(in_app_system_updates=True).count(),
            }
        }
        
        return Response(summary)


class NotificationLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notification logs.
    
    Design decisions:
    - Admin has full access, users see only their own logs
    - Read-only for regular users (logs shouldn't be edited)
    - Added filtering and analytics endpoints
    - Separate create serializer for system use
    """
    
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'status', 'user']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter logs based on user permissions"""
        if self.request.user.is_staff:
            return NotificationLog.objects.all()
        return NotificationLog.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use create serializer for creation"""
        if self.action == 'create':
            return NotificationLogCreateSerializer
        return NotificationLogSerializer
    
    def get_permissions(self):
        """
        Different permissions for different actions
        
        Reasoning: Only admins should create/modify logs, users can read their own
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        """Mark notification as delivered"""
        log = self.get_object()
        log.mark_as_delivered()
        serializer = self.get_serializer(log)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_opened(self, request, pk=None):
        """Mark notification as opened"""
        log = self.get_object()
        log.mark_as_opened()
        serializer = self.get_serializer(log)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_clicked(self, request, pk=None):
        """Mark notification as clicked"""
        log = self.get_object()
        log.mark_as_clicked()
        serializer = self.get_serializer(log)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get notification statistics
        
        Design decision: Comprehensive analytics endpoint for dashboards
        """
        queryset = self.get_queryset()
        
        # Date filtering
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
        except ValueError:
            days = 30
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(created_at__gte=start_date)
        
        # Basic counts
        total_sent = queryset.count()
        total_delivered = queryset.filter(status='delivered').count()
        total_opened = queryset.filter(status='opened').count()
        total_clicked = queryset.filter(status='clicked').count()
        
        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
        
        # Average delivery time
        avg_delivery_time = queryset.filter(
            delivered_at__isnull=False
        ).aggregate(
            avg_time=Avg('delivered_at') - Avg('created_at')
        )['avg_time']
        
        avg_delivery_seconds = avg_delivery_time.total_seconds() if avg_delivery_time else 0
        
        # Breakdown by notification type
        by_type = {}
        for notification_type in queryset.values_list('notification_type', flat=True).distinct():
            type_queryset = queryset.filter(notification_type=notification_type)
            by_type[notification_type] = {
                'total': type_queryset.count(),
                'delivered': type_queryset.filter(status='delivered').count(),
                'opened': type_queryset.filter(status='opened').count(),
                'clicked': type_queryset.filter(status='clicked').count(),
            }
        
        # Recent notifications for activity feed
        recent_notifications = queryset.order_by('-created_at')[:10]
        
        stats_data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'delivery_rate': round(delivery_rate, 2),
            'open_rate': round(open_rate, 2),
            'click_rate': round(click_rate, 2),
            'avg_delivery_time_seconds': avg_delivery_seconds,
            'by_type': by_type,
            'recent_notifications': NotificationLogSerializer(recent_notifications, many=True).data
        }
        
        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_logs(self, request):
        """
        Get current user's notification logs
        
        Design decision: Explicit endpoint for user's own logs
        """
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InAppNotificationsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for in-app notifications.
    
    Design decisions:
    - Users see only their own notifications
    - Added bulk actions for better UX
    - Separate endpoints for unread count and recent notifications
    - Auto-archive expired notifications
    """
    
    serializer_class = InAppNotificationsSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_read', 'is_archived']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter to user's notifications and auto-archive expired ones
        
        Reasoning: Clean up expired notifications automatically
        """
        queryset = InAppNotifications.objects.filter(user=self.request.user)
        
        # Auto-archive expired notifications
        expired_notifications = queryset.filter(
            expires_at__lt=timezone.now(),
            is_archived=False
        )
        expired_notifications.update(is_archived=True)
        
        return queryset
    
    def get_serializer_class(self):
        """Use create serializer for creation"""
        if self.action == 'create':
            return InAppNotificationsCreateSerializer
        return InAppNotificationsSerializer
    
    def perform_create(self, serializer):
        """Set user to current user when creating"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark single notification as read
        
        Reasoning: Common action that deserves its own endpoint
        """
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive single notification"""
        notification = self.get_object()
        notification.archive()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """
        Perform bulk actions on multiple notifications
        
        Design decision: Single endpoint for all bulk operations
        to reduce API complexity
        """
        serializer = InAppNotificationBulkActionSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        notification_ids = serializer.validated_data['notification_ids']
        action = serializer.validated_data['action']
        
        notifications = self.get_queryset().filter(id__in=notification_ids)
        updated_count = 0
        
        if action == 'mark_read':
            for notification in notifications.filter(is_read=False):
                notification.mark_as_read()
                updated_count += 1
        
        elif action == 'mark_unread':
            updated_count = notifications.filter(is_read=True).update(
                is_read=False,
                read_at=None
            )
        
        elif action == 'archive':
            for notification in notifications.filter(is_archived=False):
                notification.archive()
                updated_count += 1
        
        elif action == 'delete':
            updated_count = notifications.count()
            notifications.delete()
        
        return Response({
            'message': f'{updated_count} notifications updated',
            'action': action,
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications
        
        Reasoning: Frontend needs this for badge indicators
        """
        count = self.get_queryset().filter(is_read=False, is_archived=False).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent unread notifications (last 10)
        
        Reasoning: Quick access for dropdown notifications
        """
        notifications = self.get_queryset().filter(
            is_read=False,
            is_archived=False
        ).order_by('-created_at')[:10]
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all user's notifications as read
        
        Reasoning: Common user action for clearing notification inbox
        """
        updated_count = 0
        for notification in self.get_queryset().filter(is_read=False):
            notification.mark_as_read()
            updated_count += 1
        
        return Response({
            'message': f'{updated_count} notifications marked as read',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """
        Delete all user's archived notifications
        
        Reasoning: Allow users to clean up their notification history
        """
        deleted_count = self.get_queryset().filter(is_archived=True).count()
        self.get_queryset().filter(is_archived=True).delete()
        
        return Response({
            'message': f'{deleted_count} archived notifications deleted',
            'deleted_count': deleted_count
        })
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get available notification categories with counts
        
        Reasoning: Frontend filtering UI needs category options
        """
        queryset = self.get_queryset()
        categories = []
        
        for value, label in InAppNotifications.NOTIFICATION_PREFERENCES:
            count = queryset.filter(category=value).count()
            unread_count = queryset.filter(category=value, is_read=False).count()
            
            categories.append({
                'value': value,
                'label': label,
                'total_count': count,
                'unread_count': unread_count
            })
        
        return Response({'categories': categories})


# Additional utility views for notification management

class NotificationHealthView(viewsets.ViewSet):
    """
    Health check and monitoring endpoints for notification system
    
    Design decision: Separate viewset for system monitoring to keep
    other viewsets focused on business logic
    """
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def system_health(self, request):
        """
        Check overall health of notification system
        
        Reasoning: Help admins monitor system performance
        """
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # Recent notification volume
        recent_logs = NotificationLog.objects.filter(created_at__gte=one_hour_ago)
        daily_logs = NotificationLog.objects.filter(created_at__gte=one_day_ago)
        
        # Failed notifications
        failed_recent = recent_logs.filter(status='failed').count()
        failed_daily = daily_logs.filter(status='failed').count()
        
        # Pending notifications (scheduled but not sent)
        pending_notifications = NotificationLog.objects.filter(status='scheduled').count()
        
        # User engagement
        active_users = InAppNotifications.objects.filter(
            created_at__gte=one_day_ago
        ).values('user').distinct().count()
        
        health_data = {
            'status': 'healthy' if failed_recent < 10 else 'warning' if failed_recent < 50 else 'critical',
            'recent_notifications': recent_logs.count(),
            'daily_notifications': daily_logs.count(),
            'failed_recent': failed_recent,
            'failed_daily': failed_daily,
            'pending_notifications': pending_notifications,
            'active_users_today': active_users,
            'last_check': now.isoformat()
        }
        
        return Response(health_data)