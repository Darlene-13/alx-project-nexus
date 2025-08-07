"""
Custom filters for the Movie Recommendation Backend.
Provides advanced filtering capabilities for movies.
"""

import django_filters
from django.db.models import Q
from .models import Movie, Genre


class MovieFilter(django_filters.FilterSet):
    """
    Advanced filter set for Movie model.
    Provides multiple filtering options for complex queries.
    """
    # Basic filters
    title = django_filters.CharFilter(lookup_expr='icontains', help_text="Filter by movie title")
    director = django_filters.CharFilter(lookup_expr='icontains', help_text="Filter by director name")
    original_language = django_filters.CharFilter(help_text="Filter by original language code")
    
    # Date filters
    release_year = django_filters.NumberFilter(field_name='release_date', lookup_expr='year', help_text="Filter by release year")
    release_year_gte = django_filters.NumberFilter(field_name='release_date', lookup_expr='year__gte', help_text="Movies released in or after this year")
    release_year_lte = django_filters.NumberFilter(field_name='release_date', lookup_expr='year__lte', help_text="Movies released in or before this year")
    release_date_after = django_filters.DateFilter(field_name='release_date', lookup_expr='gte', help_text="Movies released after this date")
    release_date_before = django_filters.DateFilter(field_name='release_date', lookup_expr='lte', help_text="Movies released before this date")
    
    # Rating filters
    tmdb_rating_gte = django_filters.NumberFilter(field_name='tmdb_rating', lookup_expr='gte', help_text="Minimum TMDB rating")
    tmdb_rating_lte = django_filters.NumberFilter(field_name='tmdb_rating', lookup_expr='lte', help_text="Maximum TMDB rating")
    our_rating_gte = django_filters.NumberFilter(field_name='our_rating', lookup_expr='gte', help_text="Minimum internal rating")
    our_rating_lte = django_filters.NumberFilter(field_name='our_rating', lookup_expr='lte', help_text="Maximum internal rating")
    
    # Popularity and engagement filters
    popularity_gte = django_filters.NumberFilter(field_name='popularity_score', lookup_expr='gte', help_text="Minimum popularity score")
    popularity_lte = django_filters.NumberFilter(field_name='popularity_score', lookup_expr='lte', help_text="Maximum popularity score")
    views_gte = django_filters.NumberFilter(field_name='views', lookup_expr='gte', help_text="Minimum view count")
    likes_gte = django_filters.NumberFilter(field_name='like_count', lookup_expr='gte', help_text="Minimum like count")
    
    # Runtime filters
    runtime_gte = django_filters.NumberFilter(field_name='runtime', lookup_expr='gte', help_text="Minimum runtime in minutes")
    runtime_lte = django_filters.NumberFilter(field_name='runtime', lookup_expr='lte', help_text="Maximum runtime in minutes")
    
    # Genre filters
    genre = django_filters.ModelChoiceFilter(
        field_name='genres',
        queryset=Genre.objects.all(),
        help_text="Filter by genre"
    )
    genre_name = django_filters.CharFilter(
        field_name='genres__name',
        lookup_expr='iexact',
        help_text="Filter by genre name (case insensitive)"
    )
    genres = django_filters.ModelMultipleChoiceFilter(
        field_name='genres',
        queryset=Genre.objects.all(),
        help_text="Filter by multiple genres (OR logic)"
    )
    
    # Boolean filters
    adult = django_filters.BooleanFilter(help_text="Filter adult content (true/false)")
    has_poster = django_filters.BooleanFilter(
        field_name='poster_path',
        lookup_expr='isnull',
        exclude=True,
        help_text="Movies with poster images"
    )
    has_backdrop = django_filters.BooleanFilter(
        field_name='backdrop_path',
        lookup_expr='isnull',
        exclude=True,
        help_text="Movies with backdrop images"
    )
    
    # Cast and crew filters
    cast_member = django_filters.CharFilter(
        method='filter_by_cast_member',
        help_text="Filter by cast member name"
    )
    
    # Search across multiple fields
    search = django_filters.CharFilter(
        method='filter_by_search',
        help_text="Search across title, overview, and director"
    )
    
    # Custom range filters
    rating_range = django_filters.RangeFilter(
        field_name='tmdb_rating',
        help_text="TMDB rating range (e.g., 7.0,9.0)"
    )
    year_range = django_filters.RangeFilter(
        field_name='release_date__year',
        help_text="Release year range (e.g., 2020,2023)"
    )
    
    class Meta:
        model = Movie
        fields = []  # We define custom fields above
    
    def filter_by_cast_member(self, queryset, name, value):
        """
        Filter movies by cast member name.
        Searches within the JSON main_cast field.
        """
        if not value:
            return queryset
        
        # This uses PostgreSQL's JSON operators. For other databases, you might need different approach
        return queryset.extra(
            where=["main_cast::text ILIKE %s"],
            params=[f'%{value}%']
        )
    
    def filter_by_search(self, queryset, name, value):
        """
        Search across multiple fields using OR logic.
        """
        if not value:
            return queryset
        
        return queryset.filter(
            Q(title__icontains=value) |
            Q(original_title__icontains=value) |
            Q(overview__icontains=value) |
            Q(director__icontains=value) |
            Q(tagline__icontains=value)
        )


class GenreFilter(django_filters.FilterSet):
    """
    Filter set for Genre model.
    """
    name = django_filters.CharFilter(lookup_expr='icontains', help_text="Filter by genre name")
    has_movies = django_filters.BooleanFilter(
        method='filter_has_movies',
        help_text="Genres that have movies"
    )
    movie_count_gte = django_filters.NumberFilter(
        method='filter_movie_count_gte',
        help_text="Genres with at least this many movies"
    )
    
    class Meta:
        model = Genre
        fields = ['name']
    
    def filter_has_movies(self, queryset, name, value):
        """Filter genres that have associated movies."""
        if value:
            return queryset.filter(movies__isnull=False).distinct()
        return queryset.filter(movies__isnull=True)
    
    def filter_movie_count_gte(self, queryset, name, value):
        """Filter genres with at least the specified number of movies."""
        if not value:
            return queryset
        
        from django.db.models import Count
        return queryset.annotate(
            movie_count=Count('movies')
        ).filter(movie_count__gte=value)