"""
This is the serializers file for our movies app.
It contains serializers for our movie models.
Includes different 
"""

from rest_framework import serializers
from .models import Movie, Genre, MovieGenre
from django.db.models import Avg


class GenreSerializer(serializers.ModelSerializer):
    movie_count = serializers.SerializerMethodField()
    class Meta:
        model = Genre
        fields = ['id', 'tmdb_id', 'name', 'slug', 'movie_count', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']
        

    def get_movie_count(self, obj):
        return obj.movies.count()
    

class MovieListSerializer(serializers.ModelSerializer):
    """Serializer for the movie model.
    This can be used in list views for performance optimization.
    """
    genres = GenreSerializer(many=True, read_only=True)
    year = serializers.ReadOnlyField(source='release_date.year')
    poster_url = serializers.ReadOnlyField(source='get_poster_url')
    genre_names = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            'id', 'tmdb_id', 'title', 'release_date', 'year',
            'tmdb_rating', 'our_rating', 'popularity_score',
            'poster_url', 'runtime', 'genres', 'genre_names',
            'views', 'like_count'
        ]

class MovieDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for movie details.
    Includes all fields and computed properties.
    """
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        write_only=True,
        source='genres'
    )
    year = serializers.ReadOnlyField()
    poster_url = serializers.ReadOnlyField()
    backdrop_url = serializers.ReadOnlyField()
    genre_names = serializers.ReadOnlyField()
    main_cast_list = serializers.ReadOnlyField()
    
    class Meta:
        model = Movie
        fields = [
            'id', 'tmdb_id', 'omdb_id', 'title', 'original_title',
            'tagline', 'overview', 'release_date', 'year', 'runtime',
            'director', 'main_cast', 'main_cast_list',
            'tmdb_rating', 'tmdb_vote_count', 'omdb_rating', 'our_rating',
            'poster_path', 'poster_url', 'backdrop_path', 'backdrop_url',
            'popularity_score', 'views', 'like_count',
            'adult', 'original_language',
            'genres', 'genre_ids', 'genre_names',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'year', 'poster_url', 'backdrop_url', 'genre_names',
            'main_cast_list', 'views', 'like_count', 'created_at', 'updated_at'
        ]
    
    def validate_main_cast(self, value):
        """Validate that main_cast is a proper list of strings"""
        # ✅ FIXED: Handle both already-parsed lists and JSON strings
        if isinstance(value, list):
            # Already parsed by JSONField
            cast_list = value
        elif isinstance(value, str):
            try:
                import json
                cast_list = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("main_cast must be valid JSON array")
        else:
            # Handle None or other types
            cast_list = value if value is not None else []
            
        if not isinstance(cast_list, list):
            raise serializers.ValidationError("main_cast must be a list")
            
        for actor in cast_list:
            if not isinstance(actor, str):
                raise serializers.ValidationError("Each cast member must be a string")
                
        return cast_list
    
    def create(self, validated_data):
        """Handle genre relationships during creation"""
        genres_data = validated_data.pop('genres', [])
        movie = Movie.objects.create(**validated_data)
        movie.genres.set(genres_data)
        return movie
    
    def update(self, instance, validated_data):
        """Handle genre relationships during updates"""
        genres_data = validated_data.pop('genres', None)
        
        # Update movie fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update genres if provided
        if genres_data is not None:
            instance.genres.set(genres_data)
            
        return instance


class MovieCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer optimized for creating and updating movies.
    Excludes computed fields and focuses on writable fields.
    """
    genre_ids = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        source='genres'
    )
    
    class Meta:
        model = Movie
        fields = [
            'tmdb_id', 'omdb_id', 'title', 'original_title',
            'tagline', 'overview', 'release_date', 'runtime',
            'director', 'main_cast',
            'tmdb_rating', 'tmdb_vote_count', 'omdb_rating',
            'poster_path', 'backdrop_path',
            'popularity_score', 'adult', 'original_language',
            'genre_ids'
        ]
    
    def validate_main_cast(self, value):
        """Validate main_cast field"""
        # ✅ FIXED: Handle both already-parsed lists and JSON strings
        if isinstance(value, list):
            # Already parsed by JSONField
            cast_list = value
        elif isinstance(value, str):
            try:
                import json
                cast_list = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("main_cast must be valid JSON")
        else:
            # Handle None or other types
            cast_list = value if value is not None else []
            
        if not isinstance(cast_list, list):
            raise serializers.ValidationError("main_cast must be a list")
            
        return cast_list
    
    def create(self, validated_data):
        """Handle genre relationships during creation"""
        genres_data = validated_data.pop('genres', [])
        movie = Movie.objects.create(**validated_data)
        movie.genres.set(genres_data)
        return movie
    
    def update(self, instance, validated_data):
        """Handle genre relationships during updates"""
        genres_data = validated_data.pop('genres', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if genres_data is not None:
            instance.genres.set(genres_data)
            
        return instance


class MovieStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for movie statistics and metrics.
    Used for analytics and recommendation algorithms.
    """
    year = serializers.ReadOnlyField()
    genre_names = serializers.ReadOnlyField()
    
    class Meta:
        model = Movie
        fields = [
            'id', 'title', 'year', 'tmdb_rating', 'our_rating',
            'popularity_score', 'views', 'like_count',
            'genre_names', 'original_language', 'adult'
        ]


class MovieSearchSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for search results.
    Optimized for search performance and relevance.
    """
    year = serializers.ReadOnlyField()
    poster_url = serializers.ReadOnlyField()
    genre_names = serializers.ReadOnlyField()
    
    class Meta:
        model = Movie
        fields = [
            'id', 'tmdb_id', 'title', 'year', 'overview',
            'tmdb_rating', 'poster_url', 'genre_names',
            'popularity_score', 'director'
        ]


class MovieRecommendationSerializer(serializers.ModelSerializer):
    """
    Serializer for movie recommendations.
    Includes fields relevant for recommendation display.
    """
    year = serializers.ReadOnlyField()
    poster_url = serializers.ReadOnlyField()
    genre_names = serializers.ReadOnlyField()
    recommendation_score = serializers.FloatField(read_only=True)
    recommendation_reason = serializers.CharField(read_only=True)
    
    class Meta:
        model = Movie
        fields = [
            'id', 'tmdb_id', 'title', 'year', 'tagline',
            'tmdb_rating', 'our_rating', 'poster_url',
            'genre_names', 'director', 'popularity_score',
            'recommendation_score', 'recommendation_reason'
        ]


class GenreDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Genre with related movies.
    """
    movies = MovieListSerializer(many=True, read_only=True)
    movie_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Genre
        fields = [
            'id', 'tmdb_id', 'name', 'slug', 'created_at',
            'movie_count', 'avg_rating', 'movies'
        ]
        read_only_fields = ['id', 'slug', 'created_at']
    
    def get_movie_count(self, obj):
        """Get total number of movies in this genre"""
        return obj.movies.count()
    
    def get_avg_rating(self, obj):
        """Get average TMDB rating for movies in this genre"""
        avg = obj.movies.aggregate(avg_rating=Avg('tmdb_rating'))['avg_rating']
        return round(avg, 1) if avg else None


class MovieGenreSerializer(serializers.ModelSerializer):
    """
    Serializer for the MovieGenre through model.
    Used for explicit genre-movie relationship management.
    """
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    genre_name = serializers.CharField(source='genre.name', read_only=True)
    
    class Meta:
        model = MovieGenre
        fields = ['id', 'movie', 'genre', 'movie_title', 'genre_name']
        
    def validate(self, data):
        """Ensure the movie-genre combination doesn't already exist"""
        movie = data.get('movie')
        genre = data.get('genre')
        
        if movie and genre:
            if MovieGenre.objects.filter(movie=movie, genre=genre).exists():
                raise serializers.ValidationError(
                    "This movie-genre relationship already exists."
                )
        return data