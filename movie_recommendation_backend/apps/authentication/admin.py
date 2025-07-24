# Django admin configuration for the User model

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
import json
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.html import format_html
import csv
from django.http import HttpResponse

User = get_user_model()

class CustomUserAdmin(BaseUserAdmin):
    """
    Custom User Admin that extends Django's built-in UserAdmin.
    
    Why extend BaseUserAdmin instead of admin.ModelAdmin?
    - BaseUserAdmin provides user management features (password changes, permissions)
    - It handles user creation and editing forms properly
    - It includes security features like password hashing
    - We just add our custom fields to the existing functionality
    """
    
    # LIST VIEW CONFIGURATION

    # Fields to display in the admin list view (main user list page)
    list_display = [
        'username',           # Basic identifier
        'email',             # Contact info
        'display_name_admin', # Custom method for better display
        'is_premium',        # Business status
        'is_active',         # Account status
        'device_type',       # Device info
        'country',           # Location
        'favorite_genres_count', # Custom method
        'date_joined',       # When they joined
        'last_login',        # Activity status
    ]
    
    # Fields that are clickable links (go to edit page)
    list_display_links = ['username', 'email']
    
    # Fields that can be edited directly in the list view (without opening the detail page)
    list_editable = ['is_premium', 'is_active']
    
    # Default ordering (newest users first)
    ordering = ['-date_joined']
    
    # Number of users to show per page
    list_per_page = 25
    
    # FILTERING AND SEARCHING
    
    # Right sidebar filters in the admin list
    list_filter = [
        'is_active',          # Active/inactive users
        'is_staff',           # Staff users
        'is_superuser',       # Admin users
        'is_premium',         # Premium subscribers
        'device_type',        # iOS/Android/Web users
        'preferred_language', # Language preferences
        'country',            # Geographic distribution
        'date_joined',        # Registration date
        'last_login',         # Recent activity
    ]
    
    # Search functionality - which fields to search in
    search_fields = [
        'username',     # Username search
        'email',        # Email search
        'first_name',   # First name search
        'last_name',    # Last name search
        'bio',          # Bio text search
    ]
    
    # Help text for search box
    search_help_text = "Search by username, email, first name, last name, or bio content"
 
    # FORM FIELD ORGANIZATION
    
    # Fields to display in the user detail/edit form
    # We organize them into logical sections using fieldsets
    fieldsets = (
        # Basic Information Section
        ('Basic Information', {
            'fields': ('username', 'email', 'password'),
            'description': 'Core authentication credentials'
        }),
        
        # Personal Information Section
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'bio', 'avatar'),
            'description': 'Personal details and profile information',
            'classes': ['collapse'],  # This section starts collapsed
        }),
        
        # Contact & Location Section  
        ('Contact & Location', {
            'fields': ('phone_number', 'country', 'preferred_timezone'),
            'description': 'Contact information and geographic details',
            'classes': ['collapse'],
        }),
        
        # Preferences Section
        ('Preferences', {
            'fields': ('preferred_language', 'favorite_genres'),
            'description': 'User preferences for personalization',
            'classes': ['collapse'],
        }),
        
        # Device Information Section
        ('Device Information', {
            'fields': ('device_token', 'device_type'),
            'description': 'Device details for push notifications',
            'classes': ['collapse'],
        }),
        
        # Account Status Section
        ('Account Status', {
            'fields': ('is_active', 'is_premium', 'is_staff', 'is_superuser'),
            'description': 'Account permissions and status flags'
        }),
        
        # Timestamps Section (read-only)
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'description': 'System-generated timestamps',
            'classes': ['collapse'],
        }),
    )
    
    # Fields for the "Add User" form (when creating new users)
    add_fieldsets = (
        ('Required Information', {
            'fields': ('username', 'email', 'password1', 'password2'),
            'description': 'Basic information required to create a new user'
        }),
        ('Optional Information', {
            'fields': ('first_name', 'last_name', 'is_premium'),
            'classes': ['collapse'],
        }),
    )
    # READ ONLY FIELD
    # This are fields that should not be editable in the admin interface
    readonly_fields = [
        'last_login',  # Last login timestamp
        'date_joined', # When the user registered
        'created_at',  # Record creation timestamp
        'updated_at',  # Last update timestamp
        'display_avatar', # Custom method for avatar display
        'favorite_genres_display', # Custom method for genre count
    ]
    actions = ['export_users_csv']  # Custom action to export users to CSV

    # CUSTOM ADMIN METHODS
    # These methods provide additional functionality in the admin interface

    def display_name_admin(self, obj):
        """
        Custom method to display user's name in the admin list.
        Direct implementation without using the property.
        """
        # Direct calculation instead of using the property
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        elif obj.first_name:
            return obj.first_name
        elif obj.last_name:
            return obj.last_name
        return obj.username
    display_name_admin.short_description = 'Display Name'
    display_name_admin.admin_order_field = 'first_name'

    def favorite_genres_count(self, obj):
        """
        Display the number of favorite genres that the user has a string.
        Makes it easy than showing the JSON list preview.

        """
        try:
            genres = json.loads(obj.favorite_genres)
            count = len(genres)
            if count == 0:
                return format_html('<span class="text-muted">No genres</span>')
            elif count <= 3:
                return format_html('<span class="text-success">{} genre(s)</span>', count)
            else:
                return format_html('<span class="text-info">{} genres</span>', count)
        except (json.JSONDecodeError, TypeError):
            return format_html('<span class="text-muted">Invalid genres</span>')
        
    favorite_genres_count.short_description = 'Favorite Genres Count'

    def display_avatar(self, obj):
        """
        Custom method to display the user's avatar in the admin list.
        """
        if obj.avatar:
            return format_html('<img src="{}" alt="Avatar" style="width: 50px; height: 50px; border-radius: 50%;">', obj.avatar.url)
        return format_html('<div style="width: 100px; height: 100px; background: #ddd; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #666;">No Image</div>')
    
    display_avatar.short_description = 'Avatar'

    def favorite_genres_display(self, obj):
        """
        Custom method to display the user's favorite genres in the admin list.
        """
        try:
            genre_ids = json.loads(obj.favorite_genres)
            if not genre_ids:
                return "No favorite genres selected"
            
            #Display the IDS
            if len(genre_ids) <= 3:
                return f"Genre IDS: {', '.join(map(str, genre_ids))}"
            else:
                first_five = genre_ids[:5]
                return f"Genre IDS: {', '.join(map(str, first_five))}, ... ({len(genre_ids)} total)"
        except (json.JSONDecodeError, TypeError):
            return format_html('<span class="text-muted">Invalid genres</span>')
        
    favorite_genres_display.short_description = 'Favorite Genres'


    # CUSTOM ACTION METHODS
    def make_premium(self, request, queryset):
        """ Custom action to make select users premium members"""
        updated = queryset.update(is_premium=True)
        self.message_user(request,
                          f'{updated} users were successfully marked as premium.')
    
    make_premium.short_description = 'Make selected users premium'

    def remove_premium(self, request, queryset):
        """ Custom action to remove premium status from select users"""
        updated = queryset.update(is_premium=False)
        self.message_user(request,
                          f'{updated} users were successfully marked as non-premium.')
        
    def clear_device_tokens(self, request, queryset):
        """ Custom action to clear device tokens for selected users"""
        updated = queryset.update(device_token='')
        self.message_user(request,
                          f'{updated} users had their device tokens cleared.')
    clear_device_tokens.short_description = 'Clear device tokens for selected users'

    # Register custom actions
    actions = [
        'make_premium',
        'remove_premium',
        'clear_device_tokens',
    ]

    #ADVANCED ADMIN FEATURES
    # This section can include advanced features like custom filters, inlines, etc.
    def get_queryset(self, request):
        """
        Customizing the queryset for better performance and reduce database queries.
        """
        qs = super().get_queryset(request)
        # Apply any optimizations or prefetch_related here
        return qs
    
    def has_delete_permissions(self, request, obj=None):
        """
        Override to control delete permissions.
        For example, prevent deletion of superusers or premium users.
        """
        if obj and (obj.is_superuser or obj.is_premium):
            return False
        return super().has_delete_permissions(request, obj)
    
    def save_model(self, request, obj, form, change):
        """
        Custom logic when saving a user through admin, it is called when admin saves a user.
        """
        if change:
            print(f"Updating user: {obj.username}")
        else:
            print(f"Creating new user: {obj.username}")

        # call the parent save method to handle the actual saving
        super().save_model(request, obj, form, change)


class UserStatisticsAdmin(admin.ModelAdmin):
    """
    Admin interface for user statistics.
    This can include custom reports, analytics, etc.
    """
    list_display = ['user', 'total_movies_watched', 'total_recommendations_received']
    search_fields = ['user__username', 'user__email']

    def total_movies_watched(self, obj):
        return obj.movies_watched.count()
    
    total_movies_watched.short_description = 'Total Movies Watched'

    def total_recommendations_received(self, obj):
        return obj.recommendations_received.count()
    
    total_recommendations_received.short_description = 'Total Recommendations Received'

# REGISTER MODELS WITH ADMIN SITE
admin.site.register(User, CustomUserAdmin)

# Customize the admin site headers and title...
admin.site.site_header = "Movie Recommendation Admin"
admin.site.site_title = "Movie Recommendation Admin Portal"
admin.site.index_title = "Welcome to the Movie Recommendation Admin Portal"

#ADMIN UTILITIES
def export_users_csv(modeladmin, request, queryset):
    """
    Export selected users to a CSV file.
    This is a custom admin action that allows bulk export of user data.
    """

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Email', 'First Name', 'Last Name', 'Date Joined', 'Last Login', 'Is Premium', 'Device Type', 'Country', 'Preferred Language', 'favorite_genres', 
        ])

    for user in queryset:
        writer.writerow([
            user.username, user.email, user.first_name, user.last_name, user.date_joined, user.last_login, user.is_premium, user.device_type, user.country, user.preferred_language, user.favorite_genres
        ])

    return response