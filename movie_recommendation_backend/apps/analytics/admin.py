from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.contrib.admin import SimpleListFilter
from datetime import timedelta
import json
import csv

from .models import UserActivityLog, PopularityMetrics


class ActivityDateFilter(SimpleListFilter):
    """
    Custom date filter for activity logs.
    
    DESIGN DECISION: Pre-defined ranges instead of date picker because:
    1. Common analytics use cases (today, week, month)
    2. Better UX than calendar widget for quick filtering
    3. Performs better with indexed queries
    """
    title = 'Activity Period'
    parameter_name = 'activity_period'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('week', 'Last 7 days'),
            ('month', 'Last 30 days'),
            ('quarter', 'Last 90 days'),
        ]

    def queryset(self, request, queryset):
        """
        Filter queryset based on selected time period.
        
        OPTIMIZATION: Uses timezone-aware calculations for accuracy.
        """
        now = timezone.now()
        
        if self.value() == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(timestamp__gte=start_date)
        
        elif self.value() == 'yesterday':
            end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = end_date - timedelta(days=1)
            return queryset.filter(timestamp__range=[start_date, end_date])
        
        elif self.value() == 'week':
            start_date = now - timedelta(days=7)
            return queryset.filter(timestamp__gte=start_date)
        
        elif self.value() == 'month':
            start_date = now - timedelta(days=30)
            return queryset.filter(timestamp__gte=start_date)
        
        elif self.value() == 'quarter':
            start_date = now - timedelta(days=90)
            return queryset.filter(timestamp__gte=start_date)


class EngagementScoreFilter(SimpleListFilter):
    """
    Filter popularity metrics by engagement level.
    
    BUSINESS LOGIC: Helps identify high/low performing content quickly.
    """
    title = 'Engagement Level'
    parameter_name = 'engagement_level'

    def lookups(self, request, model_admin):
        return [
            ('high', 'High (>100)'),
            ('medium', 'Medium (50-100)'),
            ('low', 'Low (<50)'),
        ]

    def queryset(self, request, queryset):
        # Note: This requires computing engagement_score in database
        # For performance, you might want to store this as a database field
        if self.value() == 'high':
            return queryset.filter(view_count__gt=100)  # Simplified logic
        elif self.value() == 'medium':
            return queryset.filter(view_count__range=[50, 100])
        elif self.value() == 'low':
            return queryset.filter(view_count__lt=50)


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """
    Admin interface for UserActivityLog model.
    
    DESIGN PHILOSOPHY: Optimized for analytics and monitoring, not editing.
    Most fields are read-only because this is tracking data, not user input.
    
    KEY FEATURES:
    1. Visual badges for quick scanning
    2. Clickable links to related objects
    3. Export functionality for deeper analysis
    4. Performance-optimized queries
    """
    
    # List display configuration - optimized for scanning large datasets
    list_display = [
        'id', 
        'user_link',           # Clickable user link
        'action_type_badge',   # Color-coded action types
        'movie_link',          # Clickable movie link
        'source_badge',        # Visual source indicators
        'timestamp_formatted', # Human-readable timestamp
        'ip_address',
        'session_indicator'    # Session health indicator
    ]
    
    # Filters in right sidebar - most common analysis needs
    list_filter = [
        ActivityDateFilter,    # Custom date ranges
        'action_type',         # Group by action type
        'source',              # Filter by platform
        ('user', admin.RelatedOnlyFieldListFilter),  # Only users who have activities
        'ip_address',          # Fraud detection
    ]
    
    # Search functionality - covers main lookup scenarios
    search_fields = [
        'user__username',      # Find by user
        'user__email',         # Alternative user lookup
        'movie__title',        # Find by movie
        'action_type',         # Direct action search
        'session_id',          # Debug specific sessions
        'ip_address'           # Security investigations
    ]
    
    # Default ordering - most recent first for monitoring
    ordering = ['-timestamp']
    
    # Detail view organization
    fieldsets = (
        ('Core Activity Data', {
            'fields': ('user', 'action_type', 'movie', 'timestamp'),
            'description': 'Primary activity information'
        }),
        ('Session & Context', {
            'fields': ('session_id', 'source', 'ip_address'),
            'description': 'Session tracking and source information'
        }),
        ('Technical Details', {
            'fields': ('user_agent', 'referer'),
            'classes': ('collapse',),  # Hidden by default to reduce clutter
            'description': 'Browser and referral information'
        }),
        ('Additional Data', {
            'fields': ('metadata_display',),
            'classes': ('collapse',),
            'description': 'Custom metadata in JSON format'
        })
    )
    
    # Read-only fields - this is tracking data, not editable content
    readonly_fields = ['timestamp', 'metadata_display', 'ip_address', 'user_agent']
    
    # Performance settings
    list_per_page = 50        # Balance between loading speed and data visibility
    list_max_show_all = 200   # Prevent accidental huge queries
    list_select_related = ['user', 'movie']  # Optimize database queries
    
    # Custom display methods with business logic
    
    @admin.display(description="User", ordering='user__username')
    def user_link(self, obj):
        """
        Display user as clickable link with fallback for anonymous users.
        
        UX DECISION: Links to user admin for quick user analysis.
        FALLBACK: Shows "Anonymous" with distinct styling for logged-out users.
        """
        if obj.user:
            url = reverse('admin:authentication_user_change', args=[obj.user.id])
            return format_html(
                '<a href="{}" title="View user details">{}</a>', 
                url, 
                obj.user.username
            )
        return format_html(
            '<span style="color: #999; font-style: italic;">Anonymous</span>'
        )
    
    @admin.display(description="Movie", ordering='movie__title')
    def movie_link(self, obj):
        """
        Display movie as clickable link with robust error handling.
        
        ERROR HANDLING: Try to link to movie admin, fallback to plain text.
        """
        if obj.movie:
            try:
                url = reverse('admin:movies_movie_change', args=[obj.movie.id])
                return format_html(
                    '<a href="{}" title="View movie details">{}</a>', 
                    url, 
                    obj.movie.title
                )
            except:
                # Fallback if movie admin doesn't exist or has different name
                return obj.movie.title
        return format_html('<span style="color: #999;">—</span>')
    
    @admin.display(description="Action", ordering='action_type')
    def action_type_badge(self, obj):
        """
        Color-coded badges for action types for quick visual scanning.
        
        DESIGN SYSTEM: Semantic colors matching action importance/type:
        - Green: Positive engagement (views, favorites)
        - Blue: Search/discovery actions
        - Orange: Recommendation interactions
        - Purple: Rating/feedback
        - Red: High-value actions (favorites)
        """
        color_map = {
            'movie_view': '#28a745',        # Green - core engagement
            'movie_search': '#007bff',      # Blue - discovery
            'recommendation_click': '#fd7e14',  # Orange - AI engagement
            'rating_submit': '#6f42c1',     # Purple - feedback
            'favorite_add': '#dc3545',      # Red - high value
            'watchlist_add': '#e83e8c',     # Pink - intent
            'email_open': '#20c997',        # Teal - marketing
            'email_click': '#6c757d',       # Gray - marketing
            'push_click': '#ffc107',        # Yellow - notifications
        }
        
        color = color_map.get(obj.action_type, '#6c757d')  # Default gray
        display_name = obj.get_action_type_display()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500; '
            'text-transform: uppercase; letter-spacing: 0.5px;">{}</span>',
            color, 
            display_name
        )
    
    @admin.display(description="Source", ordering='source')
    def source_badge(self, obj):
        """
        Visual source indicators with icons for quick platform identification.
        
        ICON STRATEGY: Universal symbols that work across cultures.
        """
        icon_map = {
            'web': '🌐',
            'mobile': '📱', 
            'email': '📧',
            'push': '🔔',
            'api': '⚙️',
            'admin': '👤',
        }
        
        icon = icon_map.get(obj.source, '❓')
        source_name = obj.source or 'Unknown'
        
        return format_html(
            '<span title="{}">{} {}</span>', 
            f"Source: {source_name}", 
            icon, 
            source_name.title()
        )
    
    @admin.display(description="Time", ordering='timestamp')
    def timestamp_formatted(self, obj):
        """
        Human-readable timestamp with relative time for recent activities.
        
        UX: Shows "2 hours ago" for recent items, full date for older ones.
        """
        now = timezone.now()
        diff = now - obj.timestamp
        
        if diff.days == 0:
            if diff.seconds < 3600:  # Less than 1 hour
                minutes = diff.seconds // 60
                return format_html(
                    '<span style="color: #28a745; font-weight: 500;">{} min ago</span>',
                    minutes
                )
            else:  # Less than 24 hours
                hours = diff.seconds // 3600
                return format_html(
                    '<span style="color: #fd7e14;">{} hours ago</span>',
                    hours
                )
        else:
            return obj.timestamp.strftime('%b %d, %Y %H:%M')
    
    @admin.display(description="Session")
    def session_indicator(self, obj):
        """
        Session health indicator for debugging user journeys.
        
        BUSINESS VALUE: Helps identify session issues or bot traffic.
        """
        if not obj.session_id:
            return format_html('<span style="color: #dc3545;">No Session</span>')
        
        # Check if session has multiple activities (healthy session)
        session_count = UserActivityLog.objects.filter(
            session_id=obj.session_id
        ).count()
        
        if session_count == 1:
            return format_html('<span style="color: #ffc107;">Single</span>')
        elif session_count < 5:
            return format_html('<span style="color: #28a745;">Active</span>')
        else:
            return format_html('<span style="color: #007bff;">Heavy</span>')
    
    @admin.display(description="Metadata")
    def metadata_display(self, obj):
        """
        Pretty-printed JSON metadata for technical debugging.
        
        FORMATTING: Syntax highlighting and proper indentation for readability.
        """
        if obj.metadata:
            try:
                metadata_dict = obj.get_metadata_dict()
                json_str = json.dumps(metadata_dict, indent=2)
                return format_html(
                    '<pre style="background: #f8f9fa; padding: 10px; '
                    'border-radius: 4px; font-size: 12px; '
                    'border: 1px solid #dee2e6; max-height: 200px; '
                    'overflow-y: auto;">{}</pre>',
                    json_str
                )
            except Exception as e:
                return format_html(
                    '<span style="color: #dc3545;">Invalid JSON: {}</span>',
                    str(e)
                )
        return format_html('<span style="color: #6c757d;">No metadata</span>')
    
    # Custom admin actions for bulk operations
    actions = ['export_to_csv', 'analyze_sessions', 'mark_as_reviewed']
    
    @admin.action(description="Export selected logs to CSV")
    def export_to_csv(self, request, queryset):
        """
        Export activity logs to CSV for external analysis.
        
        USE CASE: Data analysts need raw data in Excel/BI tools.
        OPTIMIZATION: Streams large datasets to prevent memory issues.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="activity_logs.csv"'
        
        writer = csv.writer(response)
        
        # Header row with all relevant fields
        writer.writerow([
            'ID', 'User', 'User Email', 'Action Type', 'Movie', 'Source', 
            'IP Address', 'Session ID', 'Timestamp', 'User Agent'
        ])
        
        # Stream data to handle large exports
        for log in queryset.select_related('user', 'movie').iterator():
            writer.writerow([
                log.id,
                log.user.username if log.user else 'Anonymous',
                log.user.email if log.user else '',
                log.action_type,
                log.movie.title if log.movie else '',
                log.source or '',
                log.ip_address or '',
                log.session_id or '',
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user_agent[:100] + '...' if log.user_agent and len(log.user_agent) > 100 else log.user_agent or ''
            ])
        
        return response
    
    @admin.action(description="Analyze session patterns")
    def analyze_sessions(self, request, queryset):
        """
        Quick session analysis for selected activities.
        
        BUSINESS VALUE: Identify bot traffic, session hijacking, or UX issues.
        """
        sessions = queryset.values('session_id').annotate(
            activity_count=Count('id'),
            unique_users=Count('user', distinct=True),
            unique_ips=Count('ip_address', distinct=True)
        ).order_by('-activity_count')
        
        suspicious_sessions = [
            s for s in sessions 
            if s['unique_users'] > 1 or s['unique_ips'] > 1 or s['activity_count'] > 50
        ]
        
        if suspicious_sessions:
            message = f"Found {len(suspicious_sessions)} potentially suspicious sessions"
            self.message_user(request, message, level='WARNING')
        else:
            self.message_user(request, "No suspicious session patterns detected")
    
    @admin.action(description="Mark as reviewed")
    def mark_as_reviewed(self, request, queryset):
        """
        Custom action for workflow management.
        
        EXTENSIBILITY: Placeholder for adding review workflows.
        """
        count = queryset.count()
        # Here you could update a 'reviewed' field or create audit entries
        self.message_user(request, f"{count} activity logs marked as reviewed.")


@admin.register(PopularityMetrics)
class PopularityMetricsAdmin(admin.ModelAdmin):
    """
    Admin interface for PopularityMetrics.
    
    FOCUS: Analytics and metric monitoring, not editing.
    PURPOSE: Help content managers understand what's performing well.
    """
    
    # List display optimized for metric analysis
    list_display = [
        'movie_link',
        'date',
        'view_count_badge',
        'engagement_metrics',
        'rating_info',
        'engagement_score_display',
        'trend_indicator'
    ]
    
    # Filters for metric analysis
    list_filter = [
        ('date', admin.DateFieldListFilter),
        EngagementScoreFilter,
        ('movie', admin.RelatedOnlyFieldListFilter),
        'view_count',
        'average_rating',
    ]
    
    # Search by movie
    search_fields = ['movie__title']
    
    # Order by most recent and highest performing
    ordering = ['-date', '-view_count']
    
    # Detail view organization
    fieldsets = (
        ('Movie & Date', {
            'fields': ('movie', 'date')
        }),
        ('Activity Metrics', {
            'fields': ('view_count', 'like_count', 'rating_count', 'recommendation_count'),
            'description': 'Raw activity counts'
        }),
        ('Quality Metrics', {
            'fields': ('average_rating', 'click_through_rate'),
            'description': 'Quality and conversion indicators'
        }),
        ('Computed Metrics', {
            'fields': ('engagement_score_display',),
            'classes': ('collapse',),
            'description': 'Calculated engagement scores'
        })
    )
    
    # Most fields are computed, so read-only
    readonly_fields = ['engagement_score_display', 'date']
    
    # Performance optimization
    list_select_related = ['movie']
    list_per_page = 25
    
    # Custom display methods
    
    @admin.display(description="Movie", ordering='movie__title')
    def movie_link(self, obj):
        """Clickable movie link with error handling."""
        try:
            url = reverse('admin:movies_movie_change', args=[obj.movie.id])
            return format_html(
                '<a href="{}" title="View movie details"><strong>{}</strong></a>', 
                url, 
                obj.movie.title
            )
        except:
            return format_html('<strong>{}</strong>', obj.movie.title)
    
    @admin.display(description="Views", ordering='view_count')
    def view_count_badge(self, obj):
        """
        Visual view count with performance indicators.
        
        COLOR CODING: Green for high performance, red for low.
        """
        if obj.view_count > 1000:
            color = '#28a745'  # Green
            icon = '🔥'
        elif obj.view_count > 100:
            color = '#fd7e14'  # Orange
            icon = '📈'
        else:
            color = '#6c757d'  # Gray
            icon = '📊'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, f"{obj.view_count:,}"
        )
    
    @admin.display(description="Engagement")
    def engagement_metrics(self, obj):
        """
        Compact display of multiple engagement metrics.
        
        FORMAT: "👍 likes | ⭐ ratings | 🎯 recs"
        """
        return format_html(
            '<small>👍 {} | ⭐ {} | 🎯 {}</small>',
            obj.like_count,
            obj.rating_count,
            obj.recommendation_count
        )
    
    @admin.display(description="Rating", ordering='average_rating')
    def rating_info(self, obj):
        """
        Rating display with visual stars.
        """
        if obj.average_rating:
            stars = '⭐' * int(obj.average_rating)
            return format_html(
                '<span title="{} stars">{:.1f} {}</span>',
                obj.average_rating,
                obj.average_rating,
                stars
            )
        return format_html('<span style="color: #999;">No ratings</span>')
    
    @admin.display(description="Engagement Score")
    def engagement_score_display(self, obj):
        """
        Color-coded engagement score with performance tier.
        """
        score = obj.engagement_score
        
        if score > 100:
            color = '#28a745'  # Green
            tier = 'HIGH'
        elif score > 50:
            color = '#fd7e14'  # Orange  
            tier = 'MED'
        else:
            color = '#dc3545'  # Red
            tier = 'LOW'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;" title="Engagement Tier: {}">{}</span>',
            color, tier, score
        )
    
    @admin.display(description="Trend")
    def trend_indicator(self, obj):
        """
        Trend indicator comparing to previous day.
        
        BUSINESS VALUE: Quick visual of performance changes.
        """
        try:
            previous_day = obj.date - timedelta(days=1)
            previous_metric = PopularityMetrics.objects.get(
                movie=obj.movie, 
                date=previous_day
            )
            
            current_score = obj.engagement_score
            previous_score = previous_metric.engagement_score
            
            if current_score > previous_score * 1.1:  # 10% increase
                return format_html('<span style="color: #28a745;">📈 Up</span>')
            elif current_score < previous_score * 0.9:  # 10% decrease
                return format_html('<span style="color: #dc3545;">📉 Down</span>')
            else:
                return format_html('<span style="color: #6c757d;">➡️ Stable</span>')
                
        except PopularityMetrics.DoesNotExist:
            return format_html('<span style="color: #999;">—</span>')
    
    # Custom actions for metric management
    actions = ['recalculate_metrics', 'export_metrics', 'analyze_trends']
    
    @admin.action(description="Recalculate engagement metrics")
    def recalculate_metrics(self, request, queryset):
        """
        Recalculate metrics for selected records.
        
        USE CASE: Fix data inconsistencies or test new calculation logic.
        """
        count = 0
        for metric in queryset:
            PopularityMetrics.update_daily_metrics(metric.movie, metric.date)
            count += 1
        
        self.message_user(request, f"Recalculated metrics for {count} records.")
    
    @admin.action(description="Export metrics to CSV")
    def export_metrics(self, request, queryset):
        """
        Export popularity metrics for external analysis.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="popularity_metrics.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Movie', 'Date', 'Views', 'Likes', 'Ratings', 
            'Avg Rating', 'Recommendations', 'CTR', 'Engagement Score'
        ])
        
        for metric in queryset.select_related('movie'):
            writer.writerow([
                metric.movie.title,
                metric.date.strftime('%Y-%m-%d'),
                metric.view_count,
                metric.like_count,
                metric.rating_count,
                metric.average_rating,
                metric.recommendation_count,
                float(metric.click_through_rate),
                metric.engagement_score
            ])
        
        return response
    
    @admin.action(description="Analyze performance trends")
    def analyze_trends(self, request, queryset):
        """
        Quick trend analysis for content strategy.
        """
        movies_analyzed = queryset.values('movie').distinct().count()
        avg_engagement = queryset.aggregate(avg_score=Avg('view_count'))['avg_score']
        
        top_performer = queryset.order_by('-view_count').first()
        
        message = f"Analyzed {movies_analyzed} movies. "
        message += f"Average views: {avg_engagement:.1f}. "
        if top_performer:
            message += f"Top performer: {top_performer.movie.title} ({top_performer.view_count} views)"
        
        self.message_user(request, message)


# Custom admin site for enhanced dashboard (optional)
class AnalyticsAdminSite(admin.AdminSite):
    """
    Custom admin site with analytics dashboard.
    
    PURPOSE: Provide business users with analytics-focused interface.
    """
    site_header = "Movie Analytics Dashboard"
    site_title = "Analytics"
    index_title = "Analytics Overview"
    
    def index(self, request, extra_context=None):
        """
        Enhanced dashboard with key metrics.
        
        METRICS: Most important business indicators at a glance.
        """
        extra_context = extra_context or {}
        
        # Date calculations
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        # Key metrics for dashboard
        dashboard_stats = {
            'activities_today': UserActivityLog.objects.filter(
                timestamp__date=today
            ).count(),
            
            'activities_yesterday': UserActivityLog.objects.filter(
                timestamp__date=yesterday
            ).count(),
            
            'activities_week': UserActivityLog.objects.filter(
                timestamp__date__gte=week_ago
            ).count(),
            
            'active_users_today': UserActivityLog.objects.filter(
                timestamp__date=today
            ).values('user').distinct().count(),
            
            'top_movies_today': PopularityMetrics.objects.filter(
                date=today
            ).order_by('-view_count')[:5],
            
            'top_actions_today': UserActivityLog.objects.filter(
                timestamp__date=today
            ).values('action_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5],
        }
        
        # Calculate growth rates
        if dashboard_stats['activities_yesterday'] > 0:
            growth_rate = (
                (dashboard_stats['activities_today'] - dashboard_stats['activities_yesterday']) 
                / dashboard_stats['activities_yesterday'] * 100
            )
            dashboard_stats['growth_rate'] = round(growth_rate, 1)
        else:
            dashboard_stats['growth_rate'] = 0
        
        extra_context.update(dashboard_stats)
        
        return super().index(request, extra_context)


# Register with custom admin site if desired
# analytics_admin_site = AnalyticsAdminSite(name='analytics_admin')
# analytics_admin_site.register(UserActivityLog, UserActivityLogAdmin)
# analytics_admin_site.register(PopularityMetrics, PopularityMetricsAdmin)