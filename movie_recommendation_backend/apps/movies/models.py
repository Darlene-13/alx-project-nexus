"""
Movies Models for Movie Recommendation System

This module contains models for movie catalog management following the ERD schema.
We implement a simplified approach with JSON fields for cast/crew data while
maintaining relationships with genres through a junction table.

"""

import json
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils import timezone


def validate_json_array(value):
    """
    Custom validator to ensure the field contains a valid JSON array.
    Used for main_cast field.
    """
    try:
        data = json.loads(value) if isinstance(value, str) else value
        if not isinstance(data, list):
            raise ValidationError('This field must contain a valid JSON array.')
    except (json.JSONDecodeError, TypeError):
        raise ValidationError('This field must contain valid JSON.')


class Genre(models.Model):
    """
    Movie genres from TMDb API.
    
    Follows ERD schema exactly:
    - id: bigint PRIMARY KEY
    - tmdb_id: integer UNIQUE NOT NULL  
    - name: varchar(100) UNIQUE NOT NULL
    - slug: varchar(50) UNIQUE NOT NULL
    - created_at: timestamp NOT NULL
    """
    
    # TMDb genre ID (unique identifier from TMDb API)
    tmdb_id = models.IntegerField(unique=True,help_text='Genre ID from TMDb API')

    # Genre name (Action, Comedy, Drama, etc.)
    name = models.CharField(max_length=100, unique=True,help_text='Genre name (e.g., Action, Comedy, Drama)')

    # URL-friendly slug for genre
    slug = models.SlugField(max_length=50, unique=True, help_text='URL-friendly genre identifier')

    # Creation timestamp
    created_at = models.DateTimeField(auto_now_add=True,help_text='When this genre was added to our database')

    class Meta:
        """
        Meta configuration following ERD specifications.
        """
        db_table = 'genres'
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['name']
        
        # Database indexes for performance (as specified in ERD)
        indexes = [
            models.Index(fields=['tmdb_id'], name='idx_genres_tmdb_id'),
            models.Index(fields=['slug'], name='idx_genres_slug'),
            models.Index(fields=['name'], name='idx_genres_name'),
        ]
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-generate slug from name if not provided.
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"<Genre: {self.name} (TMDb ID: {self.tmdb_id})>"


class Movie(models.Model):
    """
    Core movie information with simplified cast/crew data.
    
    Follows ERD schema exactly with JSON fields for cast/crew:
    - All fields match the ERD specification
    - director: varchar(200) NULL (main director name)
    - main_cast: text DEFAULT '[]' (JSON array of main actor names)
    """
    # CORE IDENTIFICATION FIELDS
    
    # TMDb movie ID (primary external identifier)
    tmdb_id = models.IntegerField(unique=True,help_text='Movie ID from TMDb API')
    # IMDb movie ID (optional secondary identifier)
    imdb_id = models.CharField(max_length=20, unique=True, null=True, blank=True, help_text='Movie ID from IMDb (e.g., tt0111161)')

    # BASIC MOVIE INFORMATION
    # Movie title (as displayed)
    title = models.CharField(max_length=200, help_text='Movie title for display')
    # Original title (in original language)
    original_title = models.CharField(max_length=200, help_text='Original movie title in original language')
    
    # Movie description/plot summary
    overview = models.TextField(default='', blank=True, help_text='Movie plot summary or description')

    # Movie tagline/slogan
    tagline = models.CharField(max_length=300, default='', blank=True, help_text='Movie tagline or promotional slogan')

    # Release date
    release_date = models.DateField(null=True, blank=True, help_text='Movie release date')

    # Runtime in minutes
    runtime = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(1000)], help_text='Movie duration in minutes')
    # SIMPLIFIED CAST/CREW (Following ERD Schema)

    # Main director name (simplified from complex Person relationships)
    director = models.CharField(max_length=200, null=True, blank=True, help_text='Main director name')

    # Main cast as JSON array (simplified from complex Cast relationships)
    main_cast = models.TextField(default='[]', validators=[validate_json_array], help_text='JSON array of main actor names')

    # RATINGS AND SCORES
    
    # TMDb rating (0.0 to 10.0)
    tmdb_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(10.0)], help_text='TMDb user rating (0.0-10.0)')

    # TMDb vote count
    tmdb_vote_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text='Number of votes on TMDb')

    # IMDb rating (0.0 to 10.0)
    imdb_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(10.0)], help_text='IMDb user rating (0.0-10.0)')

    # Our platform's calculated rating
    our_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(10.0)], help_text='Our platform calculated rating based on user interactions')

    # MEDIA ASSETS    
    # Movie poster image path (from TMDb)
    poster_path = models.CharField(max_length=200, null=True, blank=True, help_text='Relative path to movie poster image on TMDb')

    # Movie backdrop image path (from TMDb)
    backdrop_path = models.CharField(max_length=200, null=True, blank=True, help_text='Relative path to movie backdrop image on TMDb')

    # PERFORMANCE METRICS
    # Popularity score (for trending calculations)
    popularity_score = models.FloatField(default=0.0, help_text='Popularity score for ranking and trending')

    # View count (how many times viewed on our platform)
    view_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text='Number of times this movie was viewed on our platform')

    # Like count (how many users liked this movie)
    like_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text='Number of users who liked this movie')
    # METADATA
    # Adult content flag
    adult = models.BooleanField(default=False, help_text='Whether this movie contains adult content')

    # Original language code (ISO 639-1)
    original_language = models.CharField(max_length=10, help_text='Original language code (e.g., en, es, fr)')

    # TIMESTAMPS
    created_at = models.DateTimeField(auto_now_add=True, help_text='When this movie was added to our database')

    updated_at = models.DateTimeField(auto_now=True, help_text='When this movie was last updated')

    # =================================================================
    # RELATIONSHIPS (Many-to-Many with Genres)
    # =================================================================
    
    # Many-to-Many relationship with genres (via junction table)
    genres = models.ManyToManyField(
        Genre,
        through='MovieGenre',
        related_name='movies',
        blank=True,
        help_text='Genres associated with this movie'
    )
    
    # =================================================================
    # META CONFIGURATION
    # =================================================================
    
    class Meta:
        """
        Meta configuration following ERD specifications.
        """
        db_table = 'movies'
        verbose_name = 'Movie'
        verbose_name_plural = 'Movies'
        ordering = ['-popularity_score', '-release_date']
        
        # High-Performance Indexes (as specified in ERD)
        indexes = [
            models.Index(fields=['tmdb_id'], name='idx_movies_tmdb_id'),
            models.Index(fields=['title'], name='idx_movies_title'),
            models.Index(fields=['-release_date'], name='idx_movies_release_date'),
            models.Index(fields=['-popularity_score'], name='idx_movies_popularity'),
            models.Index(fields=['-tmdb_rating'], name='idx_movies_rating'),
            models.Index(fields=['original_language'], name='idx_movies_language'),
            models.Index(fields=['adult'], name='idx_movies_adult'),
            models.Index(fields=['-created_at'], name='idx_movies_created_at'),
        ]
    
    # =================================================================
    # CUSTOM PROPERTIES AND METHODS
    # =================================================================
    
    @property
    def main_cast_list(self):
        """
        Parse main_cast JSON field and return as Python list.
        Returns empty list if parsing fails.
        """
        try:
            return json.loads(self.main_cast)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_main_cast(self, cast_list):
        """
        Set main cast from a list of actor names.
        
        Args:
            cast_list (list): List of actor names (strings)
        """
        if isinstance(cast_list, list):
            self.main_cast = json.dumps(cast_list)
        else:
            raise ValueError("cast_list must be a list")
    
    def add_cast_member(self, actor_name):
        """
        Add an actor to the main cast.
        
        Args:
            actor_name (str): Name of the actor to add
        """
        current_cast = self.main_cast_list
        if actor_name not in current_cast:
            current_cast.append(actor_name)
            self.set_main_cast(current_cast)
    
    def remove_cast_member(self, actor_name):
        """
        Remove an actor from the main cast.
        
        Args:
            actor_name (str): Name of the actor to remove
        """
        current_cast = self.main_cast_list
        if actor_name in current_cast:
            current_cast.remove(actor_name)
            self.set_main_cast(current_cast)
    
    @property
    def poster_url(self):
        """
        Generate full poster URL for TMDb images.
        """
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return None
    
    @property
    def backdrop_url(self):
        """
        Generate full backdrop URL for TMDb images.
        """
        if self.backdrop_path:
            return f"https://image.tmdb.org/t/p/w1280{self.backdrop_path}"
        return None
    
    @property
    def year(self):
        """
        Extract year from release date.
        """
        if self.release_date:
            return self.release_date.year
        return None
    
    @property
    def genre_names(self):
        """
        Get list of genre names for this movie.
        """
        return list(self.genres.values_list('name', flat=True))
    
    def increment_view_count(self):
        """
        Increment the view count for this movie.
        Uses F() expression to avoid race conditions.
        """
        from django.db.models import F
        Movie.objects.filter(id=self.id).update(view_count=F('view_count') + 1)
        self.refresh_from_db(fields=['view_count'])
    
    def increment_like_count(self):
        """
        Increment the like count for this movie.
        Uses F() expression to avoid race conditions.
        """
        from django.db.models import F
        Movie.objects.filter(id=self.id).update(like_count=F('like_count') + 1)
        self.refresh_from_db(fields=['like_count'])
    
    def calculate_our_rating(self):
        """
        Calculate our platform's rating based on user interactions.
        This will be implemented when we have user interactions.
        """
        # TODO: Implement when user_movie_interactions table is available
        # For now, return TMDb rating as fallback
        return self.tmdb_rating

    # DJANGO MODEL METHODS

    def clean(self):
        """
        Custom validation method.
        """
        super().clean()
        
        # Validate main_cast JSON format
        try:
            cast = json.loads(self.main_cast)
            if not isinstance(cast, list):
                raise ValidationError({
                    'main_cast': 'Main cast must be a JSON array.'
                })
            # Validate all items are strings (actor names)
            for actor in cast:
                if not isinstance(actor, str):
                    raise ValidationError({
                        'main_cast': 'All cast members must be strings (actor names).'
                    })
        except json.JSONDecodeError:
            raise ValidationError({
                'main_cast': 'Invalid JSON format for main cast.'
            })
        
        # Validate release date is not in the future (unless it's a future release)
        if self.release_date and self.release_date > timezone.now().date():
            # Allow future dates but could add a warning
            pass
        
        # Validate ratings are within bounds
        for rating_field in ['tmdb_rating', 'imdb_rating', 'our_rating']:
            rating = getattr(self, rating_field)
            if rating is not None and (rating < 0 or rating > 10):
                raise ValidationError({
                    rating_field: 'Rating must be between 0.0 and 10.0'
                })
    
    def save(self, *args, **kwargs):
        """
        Override save method to perform custom actions.
        """
        # Call clean method for validation
        self.full_clean()
        
        # Calculate our_rating if not set
        if self.our_rating is None:
            self.our_rating = self.calculate_our_rating()
        
        # Call parent save method
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        String representation of the Movie model.
        """
        year_str = f" ({self.year})" if self.year else ""
        return f"{self.title}{year_str}"
    
    def __repr__(self):
        """
        Developer representation of the Movie model.
        """
        return f"<Movie: {self.title} (TMDb ID: {self.tmdb_id})>"


class MovieGenre(models.Model):
    """
    Many-to-many relationship between movies and genres.
    
    Follows ERD schema exactly:
    - id: bigint PRIMARY KEY
    - movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    - genre_id: bigint NOT NULL REFERENCES genres(id) ON DELETE CASCADE
    - CONSTRAINT unique_movie_genre UNIQUE(movie_id, genre_id)
    """
    
    # Foreign key to Movie
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='movie_genres',
        help_text='Movie in this relationship'
    )
    
    # Foreign key to Genre
    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
        related_name='movie_genres',
        help_text='Genre in this relationship'
    )
    
    class Meta:
        """
        Meta configuration following ERD specifications.
        """
        db_table = 'movie_genres'
        verbose_name = 'Movie Genre'
        verbose_name_plural = 'Movie Genres'
        
        # Unique constraint (as specified in ERD)
        constraints = [
            models.UniqueConstraint(
                fields=['movie', 'genre'],
                name='unique_movie_genre'
            )
        ]
        
        # Database indexes for performance (as specified in ERD)
        indexes = [
            models.Index(fields=['movie'], name='idx_movie_genres_movie'),
            models.Index(fields=['genre'], name='idx_movie_genres_genre'),
        ]
    
    def __str__(self):
        return f"{self.movie.title} - {self.genre.name}"
    
    def __repr__(self):
        return f"<MovieGenre: {self.movie.title} -> {self.genre.name}>"


# =================================================================
# MODEL MANAGERS (Optional - for custom querysets)
# =================================================================

class MovieManager(models.Manager):
    """
    Custom manager for Movie model with useful querysets.
    """
    
    def popular(self):
        """
        Return movies ordered by popularity score.
        """
        return self.get_queryset().order_by('-popularity_score')
    
    def top_rated(self):
        """
        Return top-rated movies (TMDb rating > 7.0).
        """
        return self.get_queryset().filter(
            tmdb_rating__gte=7.0
        ).order_by('-tmdb_rating')
    
    def recent(self):
        """
        Return recently released movies (last 2 years).
        """
        from datetime import date, timedelta
        two_years_ago = date.today() - timedelta(days=730)
        return self.get_queryset().filter(
            release_date__gte=two_years_ago
        ).order_by('-release_date')
    
    def by_genre(self, genre_name):
        """
        Return movies filtered by genre name.
        """
        return self.get_queryset().filter(
            genres__name__icontains=genre_name
        )
    
    def search(self, query):
        """
        Search movies by title and overview.
        """
        return self.get_queryset().filter(
            models.Q(title__icontains=query) |
            models.Q(overview__icontains=query) |
            models.Q(director__icontains=query)
        )

# Add the custom manager to the Movie model
Movie.add_to_class('objects', MovieManager())