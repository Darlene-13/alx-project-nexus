from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from datetime import date
import csv
import json
import logging

from .models import User
from apps.recommendations.models import UserRecommendations, UserMovieInteraction

logger = logging.getLogger(__name__)
User = get_user_model()


class AdminConfig:
    """Configuration constants for admin interface."""
    
    LIST_PER_PAGE = 25
    MAX_INLINE_ITEMS = 10
    GENRES_DISPLAY_LIMIT = 5
    
    # CSS styles for status indicators
    STYLES = {
        'no_genres': 'color: gray;',
        'few_genres': 'color: green;',
        'many_genres': 'color: blue;',
        'invalid': 'color: red;',
        'avatar': 'width:50px;height:50px;border-radius:50%;',
        'no_avatar': 'width:50px;height:50px;background:#eee;border-radius:50%;text-align:center;'
    }


class UserUtils:
    """Utility functions for user operations."""
    
    @staticmethod
    def calculate_age(birth_date):
        """Calculate age from date of birth."""
        if not birth_date:
            return None
        today = date.today()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age

    @staticmethod
    def safe_json_parse(json_string, default=None):
        """Safely parse JSON string with fallback."""
        try:
            return json.loads(json_string) if json_string else (default or [])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse JSON: {json_string}, Error: {e}")
            return default or []

    @staticmethod
    def get_user_attribute(user, attr_name, default=''):
        """Safely get user attribute with default value."""
        return getattr(user, attr_name, default)


class ExportMixin:
    """Reusable mixin for CSV export functionality."""

    def export_users_csv(self, request, queryset):
        """Export selected users to CSV with comprehensive data."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=users_export.csv'

        writer = csv.writer(response)
        
        # Define headers
        headers = [
            'ID', 'Username', 'Email', 'Full Name', 'Age', 'Country',
            'Premium Status', 'Device Type', 'Favorite Genres Count',
            'Total Interactions', 'Total Recommendations', 'Last Login',
            'Date Joined'
        ]
        writer.writerow(headers)

        # Write user data
        for user in queryset.select_related().prefetch_related('recommendations', 'movie_interactions'):
            self._write_user_row(writer, user)

        count = queryset.count()
        self.message_user(request, f"Successfully exported {count} users to CSV.")
        return response

    def _write_user_row(self, writer, user):
        """Write a single user row to CSV."""
        age = UserUtils.calculate_age(user.date_of_birth)
        genres = UserUtils.safe_json_parse(user.favorite_genres)
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        
        row_data = [
            user.id,
            user.username,
            user.email,
            full_name,
            age,
            UserUtils.get_user_attribute(user, 'country'),
            'Yes' if UserUtils.get_user_attribute(user, 'is_premium') else 'No',
            UserUtils.get_user_attribute(user, 'device_type'),
            len(genres),
            user.movie_interactions.count(), 
            user.recommendations.count(),
            user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
            user.date_joined.strftime('%Y-%m-%d %H:%M'),
        ]
        writer.writerow(row_data)

    export_users_csv.short_description = _("Export selected users to CSV")


class BaseInlineAdmin(admin.TabularInline):
    """Base class for inline admin configurations."""
    
    extra = 0
    max_num = AdminConfig.MAX_INLINE_ITEMS
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class UserRecommendationsInline(BaseInlineAdmin):
    """Inline admin for user recommendations."""
    
    model = UserRecommendations
    fields = ['movie', 'algorithm', 'score', 'clicked', 'generated_at']
    readonly_fields = fields
    ordering = ['-score', '-generated_at']


class UserInteractionsInline(BaseInlineAdmin):
    """Inline admin for user movie interactions."""
    
    model = UserMovieInteraction
    fields = ['movie', 'interaction_type', 'rating', 'feedback_type', 'timestamp']
    readonly_fields = fields
    ordering = ['-timestamp']


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ExportMixin):
    """Enhanced user admin with analytics and recommendation management."""

    # List view configuration
    list_display = [
        'username', 'email', 'full_name_display', 'premium_status',
        'is_active', 'device_type', 'country', 'genres_summary',
        'join_date_short', 'last_login_short'
    ]
    list_display_links = ['username', 'email']
    list_editable = ['is_active']
    list_per_page = AdminConfig.LIST_PER_PAGE
    ordering = ['-date_joined']

    # Filtering and search
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'is_premium',
        'device_type', 'preferred_language', 'country',
        ('date_joined', admin.DateFieldListFilter),
        ('last_login', admin.DateFieldListFilter),
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    search_help_text = _("Search by username, email, first name, or last name")

    # Form configuration
    fieldsets = (
        (_('Authentication'), {
            'fields': ('username', 'email', 'password')
        }),
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'bio', 'avatar'),
            'classes': ['collapse']
        }),
        (_('Contact & Location'), {
            'fields': ('phone_number', 'country', 'preferred_timezone'),
            'classes': ['collapse']
        }),
        (_('Preferences'), {
            'fields': ('preferred_language', 'favorite_genres', 'genres_display'),
            'classes': ['collapse']
        }),
        (_('Device Information'), {
            'fields': ('device_token', 'device_type'),
            'classes': ['collapse']
        }),
        (_('Permissions & Status'), {
            'fields': ('is_active', 'is_premium', 'is_staff', 'is_superuser')
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )

    add_fieldsets = (
        (_('Required Information'), {
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        (_('Optional Information'), {
            'fields': ('first_name', 'last_name', 'is_premium'),
            'classes': ['collapse']
        }),
    )

    readonly_fields = [
        'last_login', 'date_joined', 'created_at', 'updated_at',
        'avatar_display', 'genres_display'
    ]

    # Actions
    actions = [
        'toggle_premium_status', 'activate_users', 'deactivate_users',
        'clear_device_tokens', 'export_users_csv'
    ]

    # Inlines
    inlines = [UserRecommendationsInline, UserInteractionsInline]

    # Display methods
    def full_name_display(self, obj):
        """Display user's full name or username as fallback."""
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name or obj.username
    full_name_display.short_description = _('Full Name')

    def premium_status(self, obj):
        """Display premium status with visual indicator."""
        if obj.is_premium:
            return format_html('<span style="color: gold;">⭐ Premium</span>')
        return format_html('<span style="color: gray;">Regular</span>')
    premium_status.short_description = _('Status')
    premium_status.admin_order_field = 'is_premium'

    def genres_summary(self, obj):
        """Display favorite genres count with color coding."""
        genres = UserUtils.safe_json_parse(obj.favorite_genres)
        count = len(genres)
        
        if count == 0:
            return format_html(f'<span style="{AdminConfig.STYLES["no_genres"]}">No genres</span>')
        elif count <= 3:
            return format_html(f'<span style="{AdminConfig.STYLES["few_genres"]}">{count} genre(s)</span>')
        return format_html(f'<span style="{AdminConfig.STYLES["many_genres"]}">{count} genres</span>')
    genres_summary.short_description = _("Favorite Genres")

    def join_date_short(self, obj):
        """Display shortened join date."""
        return obj.date_joined.strftime('%Y-%m-%d') if obj.date_joined else '-'
    join_date_short.short_description = _('Joined')
    join_date_short.admin_order_field = 'date_joined'

    def last_login_short(self, obj):
        """Display shortened last login date."""
        return obj.last_login.strftime('%Y-%m-%d') if obj.last_login else 'Never'
    last_login_short.short_description = _('Last Login')
    last_login_short.admin_order_field = 'last_login'

    def avatar_display(self, obj):
        """Display user avatar or placeholder."""
        if obj.avatar:
            return format_html(
                f'<img src="{obj.avatar.url}" style="{AdminConfig.STYLES["avatar"]}" alt="Avatar" />'
            )
        return format_html(f'<div style="{AdminConfig.STYLES["no_avatar"]}">No Avatar</div>')
    avatar_display.short_description = _("Avatar Preview")

    def genres_display(self, obj):
        """Display detailed favorite genres information."""
        genres = UserUtils.safe_json_parse(obj.favorite_genres)
        if not genres:
            return _("No favorite genres selected")
        
        displayed_genres = ', '.join(map(str, genres[:AdminConfig.GENRES_DISPLAY_LIMIT]))
        total_count = len(genres)
        
        if total_count > AdminConfig.GENRES_DISPLAY_LIMIT:
            return f"{displayed_genres}... ({total_count} total)"
        return displayed_genres
    genres_display.short_description = _("Favorite Genres Detail")

    # Action methods
    def toggle_premium_status(self, request, queryset):
        """Toggle premium status for selected users."""
        premium_count = 0
        regular_count = 0
        
        for user in queryset:
            if user.is_premium:
                user.is_premium = False
                regular_count += 1
            else:
                user.is_premium = True
                premium_count += 1
            user.save(update_fields=['is_premium'])
        
        message = f"Updated {premium_count} to premium, {regular_count} to regular."
        self.message_user(request, message)
    toggle_premium_status.short_description = _("Toggle premium status")

    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.")
    activate_users.short_description = _("Activate selected users")

    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")
    deactivate_users.short_description = _("Deactivate selected users")

    def clear_device_tokens(self, request, queryset):
        """Clear device tokens for selected users."""
        updated = queryset.update(device_token='')
        self.message_user(request, f"Device tokens cleared for {updated} user(s).")
    clear_device_tokens.short_description = _("Clear device tokens")

    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related."""
        return super().get_queryset(request).select_related().prefetch_related(
            'recommendations', 'movie_interactions'
        )


# Admin site configuration
class AdminSiteConfig:
    """Configuration for the admin site."""
    
    @staticmethod
    def configure_admin_site():
        admin.site.site_header = _("Movie Recommendation System")
        admin.site.site_title = _("Admin Portal")
        admin.site.index_title = _("Welcome to the Movie Recommendation Admin")


# Apply admin site configuration
AdminSiteConfig.configure_admin_site()