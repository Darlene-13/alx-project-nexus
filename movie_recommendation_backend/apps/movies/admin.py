from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.utils.safestring import SafeString
from django.db.models import Count, Avg
from django.forms import widgets
from django import forms
import json
from .models import Genre, Movie, MovieGenre

# Custom Widgets and Forms

class JsonTextareaWidget(widgets.Textarea):
    """
    Custom widget for JSON fields to display formatted JSON in admin.
    This makes the JSON field more readable and editable.
    """
    def format_value(self, value):
        """Format JSON data for display in textarea."""
        if value:
            try:
                # ✅ FIXED: Handle both already-parsed data and JSON strings
                if isinstance(value, (list, dict)):
                    # Already parsed - just format it nicely
                    return json.dumps(value, indent=2, ensure_ascii=False)
                elif isinstance(value, str):
                    # String - try to parse it and format nicely
                    parsed = json.loads(value)
                    return json.dumps(parsed, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass
        return value


class MovieAdminForm(forms.ModelForm):
    """
    Custom form for Movie admin to handle JSON fields properly.
    This provides better user experience when editing movies.
    """
    
    # Custom field for main_cast with better widget
    main_cast_display = forms.CharField(
        widget=JsonTextareaWidget(attrs={'rows': 6, 'cols': 60}),
        required=False,
        help_text="Enter cast members as JSON array: [\"Actor 1\", \"Actor 2\"]"
    )
    
    class Meta:
        model = Movie
        fields = '__all__'
        widgets = {
            'overview': forms.Textarea(attrs={'rows': 4, 'cols': 60}),
            'tagline': forms.TextInput(attrs={'size': 80}),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with current main_cast data."""
        super().__init__(*args, **kwargs)
        
        # Populate main_cast_display with current data
        if self.instance and self.instance.pk:
            self.fields['main_cast_display'].initial = self.instance.main_cast
    
    def clean_main_cast_display(self):
        """Validate and clean the JSON main_cast field."""
        value = self.cleaned_data.get('main_cast_display')
        if value:
            try:
                # ✅ FIXED: Handle both already-parsed data and JSON strings
                if isinstance(value, list):
                    # Already parsed - validate it
                    parsed = value
                elif isinstance(value, str):
                    # String - try to parse as JSON
                    parsed = json.loads(value)
                else:
                    # Other types - handle gracefully
                    raise forms.ValidationError("Invalid data type for main cast.")
                
                if not isinstance(parsed, list):
                    raise forms.ValidationError("Main cast must be a JSON array.")
                
                # Validate each item is a string
                for item in parsed:
                    if not isinstance(item, str):
                        raise forms.ValidationError("Each cast member must be a string.")
                
                # Return as list - JSONField will handle serialization
                return parsed
                
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format.")
        return value
    
    def save(self, commit=True):
        """Save the form, handling the main_cast field properly."""
        instance = super().save(commit=False)
        
        # Set main_cast from our custom field
        main_cast_data = self.cleaned_data.get('main_cast_display')
        if main_cast_data:
            # ✅ FIXED: Assign list directly - JSONField handles serialization
            instance.main_cast = main_cast_data
        
        if commit:
            instance.save()
        return instance

# Inline Admin Classes for Related Models

class MovieGenreInline(admin.TabularInline):
    """
    Inline admin for MovieGenre through model.
    This allows editing movie-genre relationships directly in the Movie admin.
    
    Why TabularInline:
    - Shows relationships in a compact table format
    - Easy to add/remove genre associations
    - Better UX than managing relationships separately
    """
    
    model = MovieGenre
    extra = 3  # Show 3 empty forms for adding new genres
    max_num = 10  # Limit maximum genres per movie
    
    # Customize the display
    fields = ['genre']
    autocomplete_fields = ['genre']  # Enable autocomplete for genre selection
    
    # Add some styling classes
    classes = ['collapse']  # Make it collapsible to save space

# Genre Admin
@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """
    Admin interface for Genre model.
    Simple and focused on essential functionality.
    """
    
    # DISPLAY CONFIGURATION
    list_display = [
        'name', 
        'tmdb_id', 
        'slug', 
        'movie_count',  # Custom method to show movie count
        'created_at'
    ]
    
    list_filter = ['created_at']  # Filter by creation date
    
    search_fields = ['name', 'tmdb_id']  # Enable search
    
    # FORM CONFIGURATION
    fields = ['tmdb_id', 'name']  # Only show editable fields
    readonly_fields = ['slug', 'created_at']  # Auto-generated fields
    
    # ORDERING
    ordering = ['name']  # Alphabetical by default
    
    # PERFORMANCE OPTIMIZATION
    list_per_page = 50  # Pagination
    
    def movie_count(self, obj):
        """
        Custom method to display the number of movies per genre.
        This helps admins see which genres are most popular.
        """
        count = obj.movies.count()
        if count > 0:
            # Create a link to filtered movie list
            url = reverse('admin:movies_movie_changelist') + f'?genres__id__exact={obj.id}'
            return format_html('<a href="{}">{} movies</a>', url, count)
        return '0 movies'
    
    movie_count.short_description = 'Movies'
    movie_count.admin_order_field = 'movie_count'  # Allow sorting
    
    def get_queryset(self, request):
        """
        Optimize queryset to include movie count.
        This prevents N+1 query problems.
        """
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(movie_count=Count('movies'))
        return queryset

# Movie Admin

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """
    Comprehensive admin interface for Movie model.
    Handles all the complex fields and relationships.
    """
    
    # USE CUSTOM FORM
    form = MovieAdminForm
    
    # DISPLAY CONFIGURATION
    list_display = [
        'movie_thumbnail',      # Custom method for poster image
        'title_with_year',      # Custom method combining title and year
        'director',
        'tmdb_rating_display',  # Custom method for formatted rating
        'popularity_score',
        'genre_list',           # Custom method for genre names
        'view_count_display',   # Custom method for view stats
        'created_at'
    ]
    
    list_display_links = ['movie_thumbnail', 'title_with_year']  # Clickable fields
    
    # FILTERING OPTIONS
    list_filter = [
        'adult',                    # Adult content filter
        'original_language',        # Language filter
        'release_date',            # Date range filter
        'genres',                  # Genre filter
        'tmdb_rating',             # Rating range filter
        'created_at',              # Creation date filter
    ]
    
    # SEARCH CONFIGURATION
    search_fields = [
        'title', 
        'original_title', 
        'director', 
        'tmdb_id', 
        'omdb_id',
        'overview'
    ]
    
    # FORM ORGANIZATION
    fieldsets = (
        # Basic Information Section
        ('Basic Information', {
            'fields': (
                ('title', 'original_title'),
                ('tmdb_id', 'omdb_id'),
                'tagline',
                'overview',
                ('release_date', 'runtime'),
                'director',
                'main_cast_display',  # Our custom JSON field
            ),
            'classes': ['wide'],  # Make it wider
        }),
        
        # Ratings and Metrics Section
        ('Ratings & Metrics', {
            'fields': (
                ('tmdb_rating', 'tmdb_vote_count'),
                ('omdb_rating', 'our_rating'),
                'popularity_score',
                ('views', 'like_count'),
            ),
            'classes': ['collapse'],  # Collapsible section
        }),
        
        # Media Assets Section
        ('Media Assets', {
            'fields': (
                'poster_path',
                'backdrop_path',
            ),
            'classes': ['collapse'],
        }),
        
        # Technical Details Section
        ('Technical Details', {
            'fields': (
                'original_language',
                'adult',
            ),
            'classes': ['collapse'],
        }),
        
        # Timestamps Section
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ['collapse'],
        }),
    )
    
    # READ-ONLY FIELDS
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'poster_preview',      # Custom method to show poster
        'backdrop_preview',    # Custom method to show backdrop
    ]
    
    # RELATIONSHIP HANDLING
    inlines = [MovieGenreInline]  # Include genre inline
    
    # PERFORMANCE OPTIMIZATION
    list_per_page = 25
    prefetch_related = ['genres'] 
    
    # ORDERING
    ordering = ['-created_at']  # Newest first
    
    # ACTIONS
    actions = ['mark_as_popular', 'reset_view_counts']

    # Custom Display methods
    
    def movie_thumbnail(self, obj):
        """Display a small thumbnail of the movie poster."""
        if obj.poster_path:
            poster_url = obj.poster_url
            return format_html(
                '<img src="{}" width="40" height="60" style="border-radius: 4px;" />',
                poster_url
            )
        return format_html('<div style="width:40px;height:60px;background:#f0f0f0;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:10px;">No Image</div>')
    
    movie_thumbnail.short_description = 'Poster'
    
    def title_with_year(self, obj):
        """Display title with year and rating for better readability."""
        year = f" ({obj.year})" if obj.year else ""
        rating = f" ⭐{obj.tmdb_rating}" if obj.tmdb_rating else ""
        return format_html(
            '<strong>{}</strong><span style="color: #666;">{}{}</span>',
            obj.title,
            year,
            rating
        )
    
    title_with_year.short_description = 'Title'
    title_with_year.admin_order_field = 'title'
    
    def tmdb_rating_display(self, obj):
        """Display TMDB rating with visual indicators."""
        if obj.tmdb_rating:
            # Color code based on rating
            if obj.tmdb_rating >= 8.0:
                color = '#4CAF50'  # Green for excellent
            elif obj.tmdb_rating >= 6.0:
                color = '#FF9800'  # Orange for good
            else:
                color = '#F44336'  # Red for poor
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">⭐ {}/10</span>',
                color,
                obj.tmdb_rating
            )
        return '-'
    
    tmdb_rating_display.short_description = 'TMDB Rating'
    tmdb_rating_display.admin_order_field = 'tmdb_rating'
    
    def genre_list(self, obj):
        """Display associated genres as badges."""
        genres = obj.genres.all()[:3]  # Limit to first 3 genres
        if genres:
            genre_badges = []
            for genre in genres:
                genre_badges.append(
                    f'<span style="background: #007cba; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 2px;">{genre.name}</span>'
                )
            
            # Add "..." if there are more genres
            total_count = obj.genres.count()
            if total_count > 3:
                genre_badges.append(f'<span style="color: #666;">+{total_count - 3} more</span>')
            
            return format_html(''.join(genre_badges))
        return '-'
    
    genre_list.short_description = 'Genres'
    
    def view_count_display(self, obj):
        """Display view and like counts with icons."""
        return format_html(
            '👁️ {} | 👍 {}',
            obj.views,
            obj.like_count
        )
    
    view_count_display.short_description = 'Views/Likes'
    view_count_display.admin_order_field = 'views'
    
    def poster_preview(self, obj):
        """Show full poster preview in detail view."""
        if obj.poster_path:
            return format_html(
                '<img src="{}" width="200" style="border-radius: 8px;" />',
                obj.poster_url
            )
        return 'No poster available'
    
    poster_preview.short_description = 'Poster Preview'
    
    def backdrop_preview(self, obj):
        """Show backdrop preview in detail view."""
        if obj.backdrop_path:
            return format_html(
                '<img src="{}" width="400" style="border-radius: 8px;" />',
                obj.backdrop_url
            )
        return 'No backdrop available'
    
    backdrop_preview.short_description = 'Backdrop Preview'
    #Custom Admin Actions
    def mark_as_popular(self, request, queryset):
        """Custom action to mark selected movies as popular."""
        updated = queryset.update(popularity_score=9.0)
        self.message_user(
            request,
            f'Successfully marked {updated} movies as popular.'
        )
    
    mark_as_popular.short_description = 'Mark selected movies as popular'
    
    def reset_view_counts(self, request, queryset):
        """Custom action to reset view counts for selected movies."""
        updated = queryset.update(views=0, like_count=0)
        self.message_user(
            request,
            f'Successfully reset view counts for {updated} movies.'
        )
    
    reset_view_counts.short_description = 'Reset view counts for selected movies'
    # Queryset Optimization
    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('genres')
        return queryset

# Movie Genre Admin
@admin.register(MovieGenre)
class MovieGenreAdmin(admin.ModelAdmin):
    """
    Admin for the MovieGenre through model.
    Useful for bulk management of movie-genre relationships.
    """
    
    list_display = ['movie_title', 'genre_name', 'movie_year', 'movie_rating']
    list_filter = ['genre', 'movie__release_date', 'movie__tmdb_rating']
    search_fields = ['movie__title', 'genre__name']
    
    # Enable autocomplete for better UX
    autocomplete_fields = ['movie', 'genre']
    
    # Custom display methods
    def movie_title(self, obj):
        return obj.movie.title
    movie_title.short_description = 'Movie'
    movie_title.admin_order_field = 'movie__title'
    
    def genre_name(self, obj):
        return obj.genre.name
    genre_name.short_description = 'Genre'
    genre_name.admin_order_field = 'genre__name'
    
    def movie_year(self, obj):
        return obj.movie.year
    movie_year.short_description = 'Year'
    movie_year.admin_order_field = 'movie__release_date'
    
    def movie_rating(self, obj):
        return obj.movie.tmdb_rating or '-'
    movie_rating.short_description = 'Rating'
    movie_rating.admin_order_field = 'movie__tmdb_rating'

# Admin site customization

# Customize the admin site header and title
admin.site.site_header = 'Movie Recommendation Admin'
admin.site.site_title = 'Movie Admin'
admin.site.index_title = 'Movie Management System'

# Add custom CSS if needed (optional)
class AdminConfig:
    """
    Custom admin configuration class.
    You can extend this to add more customizations.
    """
    
    @staticmethod
    def customize_admin():
        """Add any additional admin customizations here."""
        pass
    