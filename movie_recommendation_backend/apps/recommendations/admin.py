# recommendations/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from .models import UserMovieInteraction, UserRecommendations
from django.db.models import Q, F
from django.db import models
from django.utils import timezone

@admin.register(UserMovieInteraction)
class UserMovieInteractionAdmin(admin.ModelAdmin):
    """
    Admin interface for UserMovieInteraction model.
    Provides comprehensive management and analytics for user interactions.
    """
    
    # === LIST VIEW CONFIGURATION ===
    
    list_display = [
        'id',
        'user_link',           # Custom method to show clickable user
        'movie_link',          # Custom method to show clickable movie
        'interaction_type',
        'rating_display',      # Custom method for better rating display
        'feedback_badge',      # Custom method with colored badges
        'source',
        'timestamp',
        'engagement_indicator', # Visual engagement indicator
    ]
    
    list_filter = [
        'interaction_type',
        'feedback_type',
        'source',
        'timestamp',
        ('rating', admin.EmptyFieldListFilter),  # Filter by has/no rating
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'movie__title',
        'feedback_comment',
    ]
    
    date_hierarchy = 'timestamp'  # Adds date navigation
    
    # How many items per page
    list_per_page = 50
    
    # Default ordering
    ordering = ['-timestamp']
    
    # === DETAIL VIEW CONFIGURATION ===
    
    fields = [
        ('user', 'movie'),                    # Side by side
        ('interaction_type', 'source'),       # Side by side
        ('rating', 'feedback_type'),          # Side by side
        'feedback_comment',
        'metadata',
        'timestamp',
    ]
    
    readonly_fields = [
        'timestamp',
        'engagement_weight_display',  # Custom read-only field
    ]
    
    # === CUSTOM METHODS FOR LIST DISPLAY ===
    
    def user_link(self, obj):
        """Create clickable link to user's admin page"""
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return 'Anonymous'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'  # Makes column sortable
    
    def movie_link(self, obj):
        """Create clickable link to movie's admin page"""
        if obj.movie:
            # Adjust this URL pattern based on your movies app
            url = reverse('admin:movies_movie_change', args=[obj.movie.id])
            return format_html('<a href="{}">{}</a>', url, obj.movie.title)
        return 'N/A'
    movie_link.short_description = 'Movie'
    movie_link.admin_order_field = 'movie__title'
    
    def rating_display(self, obj):
        """Display rating with stars"""
        if obj.rating:
            stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
            return format_html(
                '<span title="{}/5">{}</span>',
                obj.rating,
                stars
            )
        return '-'
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'
    
    def feedback_badge(self, obj):
        """Display feedback type with colored badges"""
        if not obj.feedback_type:
            return '-'
        
        colors = {
            'positive': '#28a745',  # Green
            'negative': '#dc3545',  # Red
            'neutral': '#6c757d',   # Gray
        }
        
        color = colors.get(obj.feedback_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.feedback_type.upper()
        )
    feedback_badge.short_description = 'Feedback'
    feedback_badge.admin_order_field = 'feedback_type'
    
    def engagement_indicator(self, obj):
        """Visual indicator of engagement level"""
        weight = obj.engagement_weight
        
        if weight >= 4.0:
            color = '#28a745'  # High engagement - Green
            icon = '🔥'
        elif weight >= 2.0:
            color = '#ffc107'  # Medium engagement - Yellow
            icon = '👍'
        elif weight > 0:
            color = '#17a2b8'  # Low engagement - Blue
            icon = '👀'
        else:
            color = '#dc3545'  # Negative engagement - Red
            icon = '👎'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;" title="Weight: {}">{}</span>',
            color,
            weight,
            icon
        )
    engagement_indicator.short_description = 'Engagement'
    
    def engagement_weight_display(self, obj):
        """Read-only field showing engagement weight"""
        return f"{obj.engagement_weight} points"
    engagement_weight_display.short_description = 'Engagement Weight'
    
    # === ACTIONS ===
    
    @admin.action(description='Mark selected as positive feedback')
    def mark_positive_feedback(self, request, queryset):
        """Bulk action to mark interactions as positive"""
        updated = queryset.update(feedback_type='positive')
        self.message_user(request, f'{updated} interactions marked as positive.')
    
    @admin.action(description='Generate recommendations for these users')
    def generate_recommendations_for_users(self, request, queryset):
        """Generate recommendations for users in selected interactions"""
        users = set(queryset.values_list('user', flat=True))
        total_generated = 0
        
        for user_id in users:
            if user_id:  # Skip anonymous users
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                recs = UserRecommendations.generate_for_user(user)
                total_generated += len(recs)
        
        self.message_user(request, f'Generated {total_generated} recommendations for {len(users)} users.')
    
    actions = [mark_positive_feedback, generate_recommendations_for_users]


@admin.register(UserRecommendations)
class UserRecommendationsAdmin(admin.ModelAdmin):
    """
    Admin interface for UserRecommendations model.
    Focuses on recommendation management and performance tracking.
    """
    
    # === LIST VIEW CONFIGURATION ===
    
    list_display = [
        'id',
        'user_link',
        'movie_link',
        'score_bar',           # Visual score representation
        'algorithm_badge',     # Styled algorithm display
        'status_indicator',    # Clicked/unclicked status
        'generated_at',
        'freshness_indicator', # Age indicator
    ]
    
    list_filter = [
        'algorithm',
        'clicked',
        'generated_at',
        ('clicked_at', admin.EmptyFieldListFilter),
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'movie__title',
        'algorithm',
    ]
    
    date_hierarchy = 'generated_at'
    
    list_per_page = 50
    ordering = ['-score', '-generated_at']
    
    # === DETAIL VIEW CONFIGURATION ===
    
    fields = [
        ('user', 'movie'),
        ('score', 'algorithm'),
        ('generated_at', 'clicked'),
        'clicked_at',
        'recommendation_details',  # Custom read-only field
    ]
    
    readonly_fields = [
        'generated_at',
        'recommendation_details',
    ]
    
    # === CUSTOM METHODS FOR LIST DISPLAY ===
    
    def user_link(self, obj):
        """Clickable user link"""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def movie_link(self, obj):
        """Clickable movie link"""
        url = reverse('admin:movies_movie_change', args=[obj.movie.id])
        return format_html('<a href="{}">{}</a>', url, obj.movie.title)
    movie_link.short_description = 'Movie'
    movie_link.admin_order_field = 'movie__title'
    
    def score_bar(self, obj):
        """Visual representation of recommendation score"""
        # Score is 0-10, convert to percentage
        percentage = (obj.score / 10.0) * 100
        
        # Color based on score
        if obj.score >= 8.0:
            color = '#28a745'  # Green
        elif obj.score >= 6.0:
            color = '#ffc107'  # Yellow
        elif obj.score >= 4.0:
            color = '#fd7e14'  # Orange
        else:
            color = '#dc3545'  # Red
        
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; '
            'text-align: center; line-height: 20px; color: white; font-size: 11px;">{}</div></div>',
            percentage,
            color,
            obj.score
        )
    score_bar.short_description = 'Score'
    score_bar.admin_order_field = 'score'
    
    def algorithm_badge(self, obj):
        """Styled algorithm display"""
        colors = {
            'collaborative_filtering': '#007bff',  # Blue
            'content_based': '#28a745',            # Green
            'hybrid': '#6f42c1',                   # Purple
            'popular': '#fd7e14',                  # Orange
        }
        
        color = colors.get(obj.algorithm, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 10px; font-size: 11px;">{}</span>',
            color,
            obj.algorithm.replace('_', ' ').title()
        )
    algorithm_badge.short_description = 'Algorithm'
    algorithm_badge.admin_order_field = 'algorithm'
    
    def status_indicator(self, obj):
        """Show clicked status with icons"""
        if obj.clicked:
            return format_html(
                '<span style="color: #28a745; font-size: 16px;" title="Clicked at {}">✅</span>',
                obj.clicked_at.strftime('%Y-%m-%d %H:%M') if obj.clicked_at else 'Unknown'
            )
        else:
            return format_html(
                '<span style="color: #6c757d; font-size: 16px;" title="Not clicked">⏳</span>'
            )
    status_indicator.short_description = 'Status'
    status_indicator.admin_order_field = 'clicked'
    
    def freshness_indicator(self, obj):
        """Show recommendation age with visual indicators"""
        if obj.is_fresh:
            return format_html(
                '<span style="color: #28a745;" title="Fresh recommendation">🟢 Fresh</span>'
            )
        else:
            days_old = (timezone.now() - obj.generated_at).days
            return format_html(
                '<span style="color: #dc3545;" title="{} days old">🔴 {} days</span>',
                days_old,
                days_old
            )
    freshness_indicator.short_description = 'Freshness'
    
    def recommendation_details(self, obj):
        """Detailed info in edit view"""
        details = [
            f"Relevance Score: {obj.relevance_score}",
            f"Is Fresh: {'Yes' if obj.is_fresh else 'No'}",
            f"Click Through Time: {obj.click_through_time or 'Not clicked'}",
        ]
        return format_html('<br>'.join(details))
    recommendation_details.short_description = 'Recommendation Details'
    
    # === ACTIONS ===
    
    @admin.action(description='Mark selected as clicked')
    def mark_as_clicked(self, request, queryset):
        """Bulk action to mark recommendations as clicked"""
        updated = 0
        for rec in queryset.filter(clicked=False):
            rec.mark_as_clicked()
            updated += 1
        
        self.message_user(request, f'{updated} recommendations marked as clicked.')
    
    @admin.action(description='Refresh recommendation scores')
    def refresh_scores(self, request, queryset):
        """Recalculate recommendation scores"""
        updated = 0
        for rec in queryset:
            # This would call your score calculation logic
            new_score = UserRecommendations._calculate_recommendation_score(
                rec.user, rec.movie, rec.algorithm
            )
            rec.update_score(new_score)
            updated += 1
        
        self.message_user(request, f'Refreshed scores for {updated} recommendations.')
    
    @admin.action(description='Send notifications for selected recommendations')
    def send_notifications(self, request, queryset):
        """Send notifications for selected recommendations"""
        # Group by user
        users_recs = {}
        for rec in queryset.filter(clicked=False):
            if rec.user.id not in users_recs:
                users_recs[rec.user.id] = []
            users_recs[rec.user.id].append(rec)
        
        notifications_sent = 0
        for user_id, recs in users_recs.items():
            try:
                success = UserRecommendations._send_user_notification(user_id, recs)
                if success:
                    notifications_sent += 1
            except Exception as e:
                continue
        
        self.message_user(request, f'Sent notifications to {notifications_sent} users.')
    
    actions = [mark_as_clicked, refresh_scores, send_notifications]
    
    # === QUERYSET OPTIMIZATION ===
    
    def get_queryset(self, request):
        """Optimize database queries"""
        return super().get_queryset(request).select_related(
            'user', 'movie'  # Avoid N+1 queries
        )


# === INLINE ADMINS ===

class UserInteractionInline(admin.TabularInline):
    """
    Inline admin to show user interactions within User admin.
    Useful for seeing user activity at a glance.
    """
    model = UserMovieInteraction
    extra = 0  # Don't show empty forms
    max_num = 10  # Limit displayed interactions
    
    fields = [
        'movie',
        'interaction_type',
        'rating',
        'feedback_type',
        'timestamp',
    ]
    
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        """Show only recent interactions"""
        from django.utils import timezone
        from datetime import timedelta
        
        recent_cutoff = timezone.now() - timedelta(days=30)
        return super().get_queryset(request).filter(
            timestamp__gte=recent_cutoff
        ).select_related('movie')


class UserRecommendationInline(admin.TabularInline):
    """
    Inline admin to show recommendations within User admin.
    """
    model = UserRecommendations
    extra = 0
    max_num = 5
    
    fields = [
        'movie',
        'score',
        'algorithm',
        'clicked',
        'generated_at',
    ]
    
    readonly_fields = ['generated_at']
    
    def get_queryset(self, request):
        """Show only fresh recommendations"""
        return super().get_queryset(request).filter(
            is_fresh=True  # This might need adjustment based on your model
        ).select_related('movie').order_by('-score')


# === CUSTOM ADMIN VIEWS ===

class RecommendationAnalyticsAdmin(admin.ModelAdmin):
    """
    Custom admin for analytics and reporting.
    This creates a separate admin section for analytics.
    """
    
    def has_add_permission(self, request):
        """Disable adding - this is view-only"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing"""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Custom changelist view with analytics"""
        from django.template.response import TemplateResponse
        
        # Calculate analytics data
        context = {
            'title': 'Recommendation Analytics',
            'analytics_data': self.get_analytics_data(),
        }
        
        if extra_context:
            context.update(extra_context)
        
        return TemplateResponse(request, 'admin/recommendations_analytics.html', context)
    
    def get_analytics_data(self):
        """Calculate analytics data for dashboard"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Last 30 days data
        cutoff = timezone.now() - timedelta(days=30)
        
        total_interactions = UserMovieInteraction.objects.filter(timestamp__gte=cutoff).count()
        total_recommendations = UserRecommendations.objects.filter(generated_at__gte=cutoff).count()
        clicked_recommendations = UserRecommendations.objects.filter(
            generated_at__gte=cutoff, clicked=True
        ).count()
        
        # Algorithm performance
        algorithms = UserRecommendations.objects.values_list('algorithm', flat=True).distinct()
        algorithm_performance = []
        
        for algorithm in algorithms:
            performance = UserRecommendations.get_algorithm_performance(algorithm, days=30)
            algorithm_performance.append(performance)
        
        return {
            'total_interactions': total_interactions,
            'total_recommendations': total_recommendations,
            'overall_ctr': round(clicked_recommendations / total_recommendations * 100, 2) if total_recommendations > 0 else 0,
            'algorithm_performance': algorithm_performance,
        }


# Register the analytics admin
admin.site.register(RecommendationAnalyticsAdmin)

# === ADMIN SITE CUSTOMIZATION ===

# Customize admin site headers
admin.site.site_header = 'Movie Recommendation Admin'
admin.site.site_title = 'Movie Rec Admin'
admin.site.index_title = 'Movie Recommendation Management'


# === ADMIN FILTERS ===

class HighEngagementFilter(admin.SimpleListFilter):
    """Custom filter for high engagement interactions"""
    title = 'engagement level'
    parameter_name = 'engagement'
    
    def lookups(self, request, model_admin):
        return [
            ('high', 'High Engagement (4+)'),
            ('medium', 'Medium Engagement (2-4)'),
            ('low', 'Low Engagement (0-2)'),
            ('negative', 'Negative Engagement (<0)'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(
                models.Q(interaction_type__in=['favorite', 'watchlist']) |
                models.Q(rating__gte=4.0)
            )
        elif self.value() == 'medium':
            return queryset.filter(
                models.Q(interaction_type__in=['like', 'rating']) &
                models.Q(rating__gte=2.0, rating__lt=4.0)
            )
        # Add other conditions as needed
        return queryset


# Add custom filter to UserMovieInteractionAdmin
UserMovieInteractionAdmin.list_filter.append(HighEngagementFilter)