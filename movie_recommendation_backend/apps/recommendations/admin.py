# recommendations/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from rangefilter.filters import NumericRangeFilter
from django.http import HttpResponse
from django.db.models import Count, Avg, Q, F
from datetime import timedelta
import csv
import json
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


from .models import (
    UserMovieInteraction,
    UserRecommendations, 
    RecommendationExperiment
)

User = get_user_model()


# BASE ADMIN CLASSES & MIXINS

class BaseRecommendationAdmin(admin.ModelAdmin):
    """Base admin class with common functionality"""
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        qs = super().get_queryset(request)
        if hasattr(self.model, 'user'):
            qs = qs.select_related('user')
        if hasattr(self.model, 'movie'):
            qs = qs.select_related('movie')
        return qs
    
    def user_link(self, obj):
        """Create clickable link to user admin"""
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def movie_link(self, obj):
        """Create clickable link to movie admin"""
        if hasattr(obj, 'movie') and obj.movie:
            url = reverse('admin:movies_movie_change', args=[obj.movie.id])
            return format_html('<a href="{}">{}</a>', url, obj.movie.title)
        return '-'
    movie_link.short_description = 'Movie'
    movie_link.admin_order_field = 'movie__title'


class ExportCsvMixin:
    """Mixin to add CSV export functionality"""
    
    def export_as_csv(self, request, queryset):
        """Export selected items as CSV"""
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        writer = csv.writer(response)
        
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        
        return response
    
    export_as_csv.short_description = "Export Selected as CSV"


# USER MOVIE INTERACTION ADMIN

@admin.register(UserMovieInteraction)
class UserMovieInteractionAdmin(BaseRecommendationAdmin, ExportCsvMixin):
    """
    Admin interface for user-movie interactions.
    Provides comprehensive filtering, search, and analytics.
    """
    
    list_display = [
        'id', 'user_link', 'movie_link', 'interaction_type', 
        'rating_display', 'feedback_badge', 'engagement_weight_display',
        'source', 'is_recent_badge', 'timestamp'
    ]
    
    list_filter = [
        'interaction_type', 'feedback_type', 'source',
        ('timestamp', admin.DateFieldListFilter),
        ('rating', NumericRangeFilter),
    ]
    
    search_fields = [
        'user__username', 'user__email', 'movie__title', 
        'movie__original_title', 'feedback_comment'
    ]
    
    readonly_fields = [
        'id', 'timestamp', 'is_recent', 'is_positive_feedback', 
        'engagement_weight', 'recommendation_data'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'movie', 'interaction_type', 'timestamp')
        }),
        ('Interaction Details', {
            'fields': ('rating', 'feedback_type', 'feedback_comment', 'source', 'metadata')
        }),
        ('Computed Fields', {
            'fields': ('is_recent', 'is_positive_feedback', 'engagement_weight'),
            'classes': ('collapse',)
        }),
        ('Analytics Data', {
            'fields': ('recommendation_data',),
            'classes': ('collapse',)
        })
    )
    
    raw_id_fields = ['user', 'movie']
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    actions = ['export_as_csv', 'mark_as_positive', 'mark_as_negative', 'bulk_delete_old']
    
    def get_queryset(self, request):
        """Optimize queries and add computed annotations"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'movie').annotate(
            computed_is_positive=self._positive_feedback_annotation()
        )
    
    def _positive_feedback_annotation(self):
        """SQL annotation for positive feedback detection"""
        return Q(
            Q(interaction_type__in=['like', 'favorite', 'watchlist']) |
            Q(feedback_type='positive') |
            Q(rating__gte=4.0)
        )
    
    # Custom display methods
    def rating_display(self, obj):
        """Display rating with stars"""
        if obj.rating:
            stars = '⭐' * int(obj.rating)
            return f"{obj.rating} {stars}"
        return '-'
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'
    
    def feedback_badge(self, obj):
        """Display feedback type with color coding"""
        if obj.feedback_type == 'positive':
            return format_html('<span style="color: green;">✓ Positive</span>')
        elif obj.feedback_type == 'negative':
            return format_html('<span style="color: red;">✗ Negative</span>')
        elif obj.feedback_type == 'neutral':
            return format_html('<span style="color: orange;">− Neutral</span>')
        return '-'
    feedback_badge.short_description = 'Feedback'
    
    def engagement_weight_display(self, obj):
        """Display engagement weight with visual indicator"""
        weight = obj.engagement_weight
        if weight >= 4:
            color = 'green'
            icon = '🔥'
        elif weight >= 2:
            color = 'orange'
            icon = '👍'
        elif weight > 0:
            color = 'blue'
            icon = '👀'
        else:
            color = 'red'
            icon = '👎'
        
        return format_html(
            '<span style="color: {};">{} {}</span>', 
            color, icon, weight
        )
    engagement_weight_display.short_description = 'Engagement'
    engagement_weight_display.admin_order_field = 'engagement_weight'
    
    def is_recent_badge(self, obj):
        """Display recent status with badge"""
        if obj.is_recent:
            return format_html('<span style="color: green;">🕐 Recent</span>')
        return format_html('<span style="color: gray;">📅 Old</span>')
    is_recent_badge.short_description = 'Recency'
    
    def recommendation_data(self, obj):
        """Display formatted recommendation data"""
        data = obj.to_recommendation_data()
        return format_html('<pre>{}</pre>', json.dumps(data, indent=2, default=str))
    recommendation_data.short_description = 'ML Data'
    
    # Custom admin actions
    def mark_as_positive(self, request, queryset):
        """Mark selected interactions as positive feedback"""
        updated = queryset.update(feedback_type='positive')
        self.message_user(request, f'{updated} interactions marked as positive.')
    mark_as_positive.short_description = "Mark as positive feedback"
    
    def mark_as_negative(self, request, queryset):
        """Mark selected interactions as negative feedback"""
        updated = queryset.update(feedback_type='negative')
        self.message_user(request, f'{updated} interactions marked as negative.')
    mark_as_negative.short_description = "Mark as negative feedback"
    
    def bulk_delete_old(self, request, queryset):
        """Delete interactions older than 90 days"""
        cutoff_date = timezone.now() - timedelta(days=90)
        old_interactions = queryset.filter(timestamp__lt=cutoff_date)
        count = old_interactions.count()
        old_interactions.delete()
        self.message_user(request, f'{count} old interactions deleted.')
    bulk_delete_old.short_description = "Delete interactions older than 90 days"


# USER RECOMMENDATIONS ADMIN
@admin.register(UserRecommendations)
class UserRecommendationsAdmin(BaseRecommendationAdmin, ExportCsvMixin):
    """
    Admin interface for user recommendations.
    Focuses on performance analytics and recommendation quality.
    """
    
    list_display = [
        'id', 'user_link', 'movie_link', 'score_display', 'algorithm_badge',
        'freshness_indicator', 'click_status', 'generated_at'
    ]
    
    list_filter = [
        'algorithm', 'clicked',
        ('generated_at', admin.DateFieldListFilter),
        ('score', NumericRangeFilter),
    ]
    
    search_fields = [
        'user__username', 'user__email', 'movie__title',
        'movie__original_title', 'algorithm'
    ]
    
    readonly_fields = [
        'id', 'generated_at', 'is_fresh', 'relevance_score', 
        'click_through_time', 'api_format'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'movie', 'algorithm', 'score', 'generated_at')
        }),
        ('Performance Tracking', {
            'fields': ('clicked', 'clicked_at')
        }),
        ('Computed Metrics', {
            'fields': ('is_fresh', 'relevance_score', 'click_through_time'),
            'classes': ('collapse',)
        }),
        ('API Data', {
            'fields': ('api_format',),
            'classes': ('collapse',)
        })
    )
    
    raw_id_fields = ['user', 'movie']
    date_hierarchy = 'generated_at'
    list_per_page = 50
    
    actions = [
        'export_as_csv', 'mark_as_clicked', 'refresh_scores', 
        'cleanup_old_recommendations', 'generate_performance_report'
    ]
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        return super().get_queryset(request).select_related('user', 'movie')
    
    # Custom display methods
    def score_display(self, obj):
        """Display score with visual bar"""
        width = min(obj.score * 10, 100)  # Scale to percentage
        color = 'green' if obj.score >= 7 else 'orange' if obj.score >= 5 else 'red'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0;">'
            '<div style="width: {}px; height: 20px; background-color: {}; text-align: center; color: white;">'
            '{:.1f}</div></div>',
            width, color, obj.score
        )
    score_display.short_description = 'Score'
    score_display.admin_order_field = 'score'
    
    def algorithm_badge(self, obj):
        """Display algorithm with color coding"""
        colors = {
            'collaborative_filtering': 'blue',
            'content_based': 'green', 
            'hybrid': 'purple',
            'trending': 'orange',
            'demographic': 'teal'
        }
        color = colors.get(obj.algorithm, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
            color, obj.algorithm
        )
    algorithm_badge.short_description = 'Algorithm'
    
    def freshness_indicator(self, obj):
        """Display freshness with visual indicator"""
        if obj.is_fresh:
            return format_html('<span style="color: green;">🟢 Fresh</span>')
        else:
            days_old = (timezone.now() - obj.generated_at).days
            return format_html('<span style="color: red;">🔴 Stale ({}d)</span>', days_old)
    freshness_indicator.short_description = 'Freshness'
    
    def click_status(self, obj):
        """Display click status with metrics"""
        if obj.clicked:
            ctt = obj.click_through_time
            if ctt:
                return format_html('<span style="color: green;">✓ Clicked ({})</span>', str(ctt))
            return format_html('<span style="color: green;">✓ Clicked</span>')
        return format_html('<span style="color: gray;">○ Not Clicked</span>')
    click_status.short_description = 'Click Status'
    
    def api_format(self, obj):
        """Display API formatted data"""
        data = obj.to_api_format()
        return format_html('<pre>{}</pre>', json.dumps(data, indent=2, default=str))
    api_format.short_description = 'API Format'
    
    # Custom admin actions
    def mark_as_clicked(self, request, queryset):
        """Mark selected recommendations as clicked"""
        updated = 0
        for rec in queryset:
            if not rec.clicked:
                rec.mark_as_clicked()
                updated += 1
        self.message_user(request, f'{updated} recommendations marked as clicked.')
    mark_as_clicked.short_description = "Mark as clicked"
    
    def refresh_scores(self, request, queryset):
        """Refresh recommendation scores (placeholder)"""
        # This would integrate with your ML pipeline
        count = queryset.count()
        self.message_user(request, f'Score refresh initiated for {count} recommendations.')
    refresh_scores.short_description = "Refresh recommendation scores"
    
    def cleanup_old_recommendations(self, request, queryset):
        """Remove old unclicked recommendations"""
        old_count = UserRecommendations.cleanup_old_recommendations(days=30)
        self.message_user(request, f'{old_count} old recommendations cleaned up.')
    cleanup_old_recommendations.short_description = "Cleanup old recommendations"
    
    def generate_performance_report(self, request, queryset):
        """Generate performance report for selected algorithms"""
        algorithms = queryset.values_list('algorithm', flat=True).distinct()
        report_data = []
        
        for algorithm in algorithms:
            performance = UserRecommendations.get_algorithm_performance(algorithm)
            report_data.append(performance)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=recommendation_performance.csv'
        
        writer = csv.writer(response)
        writer.writerow(['Algorithm', 'Total Recs', 'Clicked', 'CTR', 'Avg Score'])
        
        for data in report_data:
            writer.writerow([
                data['algorithm'], data['total_recommendations'],
                data['clicked_recommendations'], data['click_through_rate'],
                data['average_score']
            ])
        
        return response
    generate_performance_report.short_description = "Generate performance report"

# RECOMMENDATION EXPERIMENT ADMIN
@admin.register(RecommendationExperiment)
class RecommendationExperimentAdmin(admin.ModelAdmin, ExportCsvMixin):
    """
    Admin interface for A/B testing experiments.
    Provides experiment management and statistical analysis.
    """
    
    list_display = [
        'name', 'algorithm_comparison', 'status_badge', 'progress_bar',
        'traffic_split_display', 'target_metric', 'significance_indicator',
        'start_date', 'end_date'
    ]
    
    list_filter = [
        'is_active', 'target_metric', 'algorithm_a', 'algorithm_b',
        ('start_date', admin.DateFieldListFilter),
    ]
    
    search_fields = ['name', 'description', 'algorithm_a', 'algorithm_b']
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'is_running', 'is_completed',
        'duration_days', 'progress_percentage', 'has_significant_result',
        'experiment_metrics', 'statistical_summary'
    ]
    
    fieldsets = (
        ('Experiment Configuration', {
            'fields': ('name', 'description', 'algorithm_a', 'algorithm_b', 'traffic_split')
        }),
        ('Schedule & Metrics', {
            'fields': ('start_date', 'end_date', 'target_metric', 'minimum_sample_size', 'confidence_level')
        }),
        ('Status & Control', {
            'fields': ('is_active', 'created_by')
        }),
        ('Statistical Results', {
            'fields': ('statistical_significance', 'winner_algorithm', 'p_value', 'effect_size'),
            'classes': ('collapse',)
        }),
        ('Computed Fields', {
            'fields': ('is_running', 'is_completed', 'duration_days', 'progress_percentage', 'has_significant_result'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('experiment_metrics', 'statistical_summary'),
            'classes': ('collapse',)
        })
    )
    
    raw_id_fields = ['created_by']
    date_hierarchy = 'created_at'
    list_per_page = 25
    
    actions = [
        'export_as_csv', 'stop_experiments', 'calculate_results',
        'extend_experiments', 'clone_experiments'
    ]
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('created_by')
    
    # Custom display methods
    def algorithm_comparison(self, obj):
        """Display algorithm comparison"""
        return format_html(
            '<strong>{}</strong> vs <strong>{}</strong>',
            obj.algorithm_a, obj.algorithm_b
        )
    algorithm_comparison.short_description = 'A vs B'
    
    def status_badge(self, obj):
        """Display experiment status with color coding"""
        if obj.is_running:
            return format_html('<span style="color: green;">🟢 Running</span>')
        elif obj.is_completed:
            return format_html('<span style="color: blue;">🔵 Completed</span>')
        elif obj.is_active:
            return format_html('<span style="color: orange;">🟡 Scheduled</span>')
        else:
            return format_html('<span style="color: red;">🔴 Stopped</span>')
    status_badge.short_description = 'Status'
    
    def progress_bar(self, obj):
        """Display progress bar"""
        progress = obj.progress_percentage
        width = min(progress, 100)
        color = 'green' if progress >= 100 else 'blue'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0;">'
            '<div style="width: {}px; height: 20px; background-color: {}; text-align: center; color: white;">'
            '{:.0f}%</div></div>',
            width, color, progress
        )
    progress_bar.short_description = 'Progress'
    
    def traffic_split_display(self, obj):
        """Display traffic split with visual representation"""
        split_a = int((1 - obj.traffic_split) * 100)
        split_b = int(obj.traffic_split * 100)
        
        return format_html(
            'A: {}% | B: {}%',
            split_a, split_b
        )
    traffic_split_display.short_description = 'Split'
    
    def significance_indicator(self, obj):
        """Display statistical significance"""
        if obj.has_significant_result:
            return format_html('<span style="color: green;">✓ Significant</span>')
        elif obj.p_value is not None:
            return format_html('<span style="color: orange;">~ Trending</span>')
        else:
            return format_html('<span style="color: gray;">○ No Data</span>')
    significance_indicator.short_description = 'Significance'
    
    def experiment_metrics(self, obj):
        """Display current experiment metrics"""
        try:
            metrics = obj.calculate_metrics()
            if metrics:
                return format_html('<pre>{}</pre>', json.dumps(metrics, indent=2, default=str))
            return 'No data available'
        except Exception as e:
            return f'Error calculating metrics: {e}'
    experiment_metrics.short_description = 'Current Metrics'
    
    def statistical_summary(self, obj):
        """Display statistical analysis summary"""
        summary = {
            'p_value': obj.p_value,
            'effect_size': obj.effect_size,
            'statistical_significance': obj.statistical_significance,
            'winner': obj.winner_algorithm,
            'confidence_level': obj.confidence_level
        }
        return format_html('<pre>{}</pre>', json.dumps(summary, indent=2, default=str))
    statistical_summary.short_description = 'Statistical Summary'
    
    # Custom admin actions
    def stop_experiments(self, request, queryset):
        """Stop selected experiments"""
        stopped = 0
        for experiment in queryset.filter(is_active=True):
            experiment.stop_experiment()
            stopped += 1
        self.message_user(request, f'{stopped} experiments stopped.')
    stop_experiments.short_description = "Stop selected experiments"
    
    def calculate_results(self, request, queryset):
        """Calculate statistical results for experiments"""
        # This would integrate with your statistical analysis pipeline
        count = queryset.count()
        self.message_user(request, f'Results calculation initiated for {count} experiments.')
    calculate_results.short_description = "Calculate statistical results"
    
    def extend_experiments(self, request, queryset):
        """Extend experiment end dates by 7 days"""
        extended = 0
        for experiment in queryset.filter(is_active=True):
            experiment.end_date += timedelta(days=7)
            experiment.save()
            extended += 1
        self.message_user(request, f'{extended} experiments extended by 7 days.')
    extend_experiments.short_description = "Extend by 7 days"
    
    def clone_experiments(self, request, queryset):
        """Clone selected experiments"""
        cloned = 0
        for experiment in queryset:
            new_experiment = RecommendationExperiment.objects.create(
                name=f"{experiment.name} (Clone)",
                description=experiment.description,
                algorithm_a=experiment.algorithm_a,
                algorithm_b=experiment.algorithm_b,
                traffic_split=experiment.traffic_split,
                start_date=timezone.now() + timedelta(days=1),
                end_date=timezone.now() + timedelta(days=experiment.duration_days + 1),
                target_metric=experiment.target_metric,
                minimum_sample_size=experiment.minimum_sample_size,
                confidence_level=experiment.confidence_level,
                created_by=request.user,
                is_active=False
            )
            cloned += 1
        self.message_user(request, f'{cloned} experiments cloned.')
    clone_experiments.short_description = "Clone selected experiments"


# USER ADMIN ENHANCEMENT

class UserRecommendationsInline(admin.TabularInline):
    """Inline admin for viewing user recommendations in User admin"""
    model = UserRecommendations
    extra = 0
    max_num = 10
    fields = ['movie', 'algorithm', 'score', 'clicked', 'generated_at']
    readonly_fields = ['movie', 'algorithm', 'score', 'clicked', 'generated_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class UserInteractionsInline(admin.TabularInline):
    """Inline admin for viewing user interactions in User admin"""
    model = UserMovieInteraction
    extra = 0
    max_num = 10
    fields = ['movie', 'interaction_type', 'rating', 'feedback_type', 'timestamp']
    readonly_fields = ['movie', 'interaction_type', 'rating', 'feedback_type', 'timestamp']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# CUSTOM USER ADMIN (if you want to extend User admin)

class EnhancedUserAdmin(BaseUserAdmin):
    """
    Enhanced User admin that shows recommendation preferences and statistics.
    """
    
    # Add recommendation fields to User admin
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Recommendation Preferences', {
            'fields': (
                'favorite_genres', 'algorithm_preference', 'diversity_preference',
                'novelty_preference', 'content_rating_preference', 'preferred_decade'
            ),
            'classes': ('collapse',)
        }),
        ('Onboarding Status', {
            'fields': (
                'onboarding_completed', 'onboarding_completed_at',
                'cold_start_preferences_collected'
            ),
            'classes': ('collapse',)
        }),
        ('Privacy Settings', {
            'fields': ('allow_demographic_targeting', 'data_usage_consent'),
            'classes': ('collapse',)
        }),
    )
    
    # Add inlines for recommendations and interactions
    inlines = BaseUserAdmin.inlines + [UserRecommendationsInline, UserInteractionsInline]
    
    # Add recommendation-related list display
    list_display = BaseUserAdmin.list_display + ('onboarding_completed', 'has_preferences')
    
    def has_preferences(self, obj):
        """Check if user has set recommendation preferences"""
        favorite_genres = getattr(obj, 'favorite_genres', [])
        return bool(favorite_genres)
    has_preferences.boolean = True
    has_preferences.short_description = 'Has Preferences'
    
    # Add recommendation-related filters
    list_filter = BaseUserAdmin.list_filter + (
        'onboarding_completed', 'allow_demographic_targeting'
    )


# Only register enhanced User admin if you want to replace the default
# Uncomment the lines below if you want to use the enhanced User admin
# admin.site.unregister(User)
# admin.site.register(User, EnhancedUserAdmin)

# ADMIN SITE CUSTOMIZATION

# Customize admin site headers
admin.site.site_header = "Movie Recommendation System Admin"
admin.site.site_title = "Recommendations Admin"
admin.site.index_title = "Welcome to Recommendations Administration"


# Custom admin site with dashboard statistics
class RecommendationAdminSite(admin.AdminSite):
    """Custom admin site with additional functionality"""
    
    def get_app_list(self, request):
        """Customize the admin index page with quick stats"""
        app_list = super().get_app_list(request)
        
        # Add quick stats to the recommendations app
        for app in app_list:
            if app['name'] == 'Recommendations':
                # Calculate quick stats
                today = timezone.now().date()
                stats = {
                    'interactions_today': UserMovieInteraction.objects.filter(
                        timestamp__date=today
                    ).count(),
                    'recommendations_generated_today': UserRecommendations.objects.filter(
                        generated_at__date=today
                    ).count(),
                    'active_experiments': RecommendationExperiment.objects.filter(
                        is_active=True
                    ).count(),
                    'onboarded_users': User.objects.filter(
                        onboarding_completed=True
                    ).count()
                }
                
                app['description'] = (
                    f"Today: {stats['interactions_today']} interactions, "
                    f"{stats['recommendations_generated_today']} recommendations generated. "
                    f"Active: {stats['active_experiments']} experiments, "
                    f"{stats['onboarded_users']} onboarded users."
                )
        
        return app_list

    def index(self, request, extra_context=None):
        """Add dashboard data to admin index"""
        extra_context = extra_context or {}
        
        # Add system health indicators
        now = timezone.now()
        extra_context.update({
            'system_health': {
                'total_users': User.objects.filter(is_active=True).count(),
                'total_interactions': UserMovieInteraction.objects.count(),
                'total_recommendations': UserRecommendations.objects.count(),
                'fresh_recommendations': UserRecommendations.objects.filter(
                    generated_at__gte=now - timedelta(days=7)
                ).count(),
                'running_experiments': RecommendationExperiment.objects.filter(
                    is_active=True,
                    start_date__lte=now,
                    end_date__gte=now
                ).count(),
            }
        })
        
        return super().index(request, extra_context)


# Uncomment to use custom admin site
# recommendation_admin_site = RecommendationAdminSite(name='recommendation_admin')