from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Count
import csv
import json

from .models import UserActivityLog, PopularityMetrics


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """
    Clean admin interface for UserActivityLog.
    Focus: Quick monitoring and basic analytics.
    """
    
    list_display = [
        'id', 'user_display', 'action_type_badge', 'movie_display', 
        'source', 'timestamp', 'ip_address'
    ]
    
    list_filter = [
        'action_type',
        'source', 
        ('timestamp', admin.DateFieldListFilter),
        ('user', admin.RelatedOnlyFieldFilter),
    ]
    
    search_fields = [
        'user__username', 'movie__title', 'action_type', 'session_id'
    ]
    
    ordering = ['-timestamp']
    readonly_fields = ['timestamp', 'metadata_json']
    list_per_page = 50
    list_select_related = ['user', 'movie']
    
    fieldsets = (
        ('Activity Info', {
            'fields': ('user', 'action_type', 'movie', 'timestamp')
        }),
        ('Session & Source', {
            'fields': ('session_id', 'source', 'ip_address')
        }),
        ('Technical', {
            'fields': ('user_agent', 'referer', 'metadata_json'),
            'classes': ('collapse',)
        }),
    )
    
    def user_display(self, obj):
        """Show user with link or Anonymous."""
        if obj.user:
            try:
                url = reverse('admin:auth_user_change', args=[obj.user.id])
                return format_html('<a href="{}">{}</a>', url, obj.user.username)
            except:
                return obj.user.username
        return format_html('<em>Anonymous</em>')
    user_display.short_description = "User"
    user_display.admin_order_field = 'user__username'
    
    def movie_display(self, obj):
        """Show movie with link if available."""
        if obj.movie:
            try:
                url = reverse('admin:movies_movie_change', args=[obj.movie.id])
                return format_html('<a href="{}">{}</a>', url, obj.movie.title)
            except:
                return obj.movie.title
        return "-"
    movie_display.short_description = "Movie"
    movie_display.admin_order_field = 'movie__title'
    
    def action_type_badge(self, obj):
        """Simple colored badges for action types."""
        colors = {
            'movie_view': '#28a745',
            'movie_search': '#007bff', 
            'recommendation_click': '#fd7e14',
            'rating_submit': '#6f42c1',
            'favorite_add': '#dc3545',
            'watchlist_add': '#e83e8c',
            'email_open': '#20c997',
            'email_click': '#6c757d',
            'push_click': '#ffc107',
        }
        color = colors.get(obj.action_type, '#6c757d')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_action_type_display()
        )
    action_type_badge.short_description = "Action"
    action_type_badge.admin_order_field = 'action_type'
    
    def metadata_json(self, obj):
        """Display metadata in readable format."""
        if obj.metadata:
            try:
                data = obj.get_metadata_dict()
                return format_html(
                    '<pre style="font-size: 11px; max-height: 150px; overflow-y: auto;">{}</pre>',
                    json.dumps(data, indent=2)
                )
            except:
                return obj.metadata
        return "No metadata"
    metadata_json.short_description = "Metadata"
    
    # Simple export action
    actions = ['export_csv']
    
    def export_csv(self, request, queryset):
        """Export selected logs to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="activity_logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'User', 'Action', 'Movie', 'Source', 'Timestamp'])
        
        for log in queryset.select_related('user', 'movie'):
            writer.writerow([
                log.id,
                log.user.username if log.user else 'Anonymous',
                log.action_type,
                log.movie.title if log.movie else '',
                log.source or '',
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_csv.short_description = "Export to CSV"


@admin.register(PopularityMetrics)
class PopularityMetricsAdmin(admin.ModelAdmin):
    """
    Admin interface for PopularityMetrics.
    Focus: View metrics and trends.
    """
    
    list_display = [
        'movie_display', 'date', 'view_count', 'like_count', 
        'rating_count', 'average_rating', 'engagement_score_display'
    ]
    
    list_filter = [
        ('date', admin.DateFieldListFilter),
        ('movie', admin.RelatedOnlyFieldFilter),
        'view_count',
        'average_rating',
    ]
    
    search_fields = ['movie__title']
    ordering = ['-date', '-view_count']
    readonly_fields = ['engagement_score_display']
    list_per_page = 30
    list_select_related = ['movie']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('movie', 'date')
        }),
        ('Metrics', {
            'fields': (
                'view_count', 'like_count', 'rating_count', 
                'average_rating', 'recommendation_count', 'click_through_rate'
            )
        }),
        ('Computed', {
            'fields': ('engagement_score_display',),
            'classes': ('collapse',)
        })
    )
    
    def movie_display(self, obj):
        """Show movie with link."""
        try:
            url = reverse('admin:movies_movie_change', args=[obj.movie.id])
            return format_html('<a href="{}">{}</a>', url, obj.movie.title)
        except:
            return obj.movie.title
    movie_display.short_description = "Movie"
    movie_display.admin_order_field = 'movie__title'
    
    def engagement_score_display(self, obj):
        """Show engagement score with color coding."""
        score = obj.engagement_score
        
        if score > 100:
            color = '#28a745'
        elif score > 50:
            color = '#fd7e14'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, score
        )
    engagement_score_display.short_description = "Engagement Score"
    
    # Export action
    actions = ['export_metrics']
    
    def export_metrics(self, request, queryset):
        """Export metrics to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="popularity_metrics.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Movie', 'Date', 'Views', 'Likes', 'Ratings', 
            'Avg Rating', 'CTR', 'Engagement Score'
        ])
        
        for metric in queryset.select_related('movie'):
            writer.writerow([
                metric.movie.title,
                metric.date,
                metric.view_count,
                metric.like_count,
                metric.rating_count,
                metric.average_rating or 0,
                float(metric.click_through_rate),
                metric.engagement_score
            ])
        
        return response
    export_metrics.short_description = "Export metrics to CSV"


# Optional: Add some admin site customization
admin.site.site_header = "Movie Analytics Admin"
admin.site.site_title = "Analytics"
admin.site.index_title = "Analytics Dashboard"