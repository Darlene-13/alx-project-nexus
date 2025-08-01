# recommendations/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserMovieInteraction, UserRecommendations
from django.db.models import Q, F
from django.db import models

User = get_user_model()


class UserMovieInteractionSerializer(serializers.ModelSerializer):
    """
    Serializer for UserMovieInteraction model.
    Handles conversion between Python objects and JSON for API responses.
    """
    
    # Read-only fields that are calculated/computed
    is_recent = serializers.ReadOnlyField()
    is_positive_feedback = serializers.ReadOnlyField()
    engagement_weight = serializers.ReadOnlyField()
    
    # Display fields for better API responses
    user_username = serializers.CharField(source='user.username', read_only=True)
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    interaction_type_display = serializers.CharField(source='get_interaction_type_display', read_only=True)
    
    class Meta:
        model = UserMovieInteraction
        fields = [
            'id',
            'user',
            'user_username',  # Display field
            'movie',
            'movie_title',    # Display field
            'interaction_type',
            'interaction_type_display',  # Human-readable
            'rating',
            'feedback_type',
            'feedback_comment',
            'metadata',
            'source',
            'timestamp',
            # Computed properties
            'is_recent',
            'is_positive_feedback',
            'engagement_weight',
        ]
        read_only_fields = [
            'id',
            'timestamp',
            'user_username',
            'movie_title',
            'interaction_type_display',
            'is_recent',
            'is_positive_feedback',
            'engagement_weight',
        ]
    
    def validate_rating(self, value):
        """Custom validation for rating field"""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # If interaction_type is 'rating', rating should be provided
        if data.get('interaction_type') == 'rating' and not data.get('rating'):
            raise serializers.ValidationError({
                'rating': 'Rating is required when interaction_type is "rating"'
            })
        
        return data


class UserMovieInteractionCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating interactions.
    Used when you only need basic fields for creation.
    """
    
    class Meta:
        model = UserMovieInteraction
        fields = [
            'user',
            'movie',
            'interaction_type',
            'rating',
            'feedback_type',
            'feedback_comment',
            'source',
            'metadata',
        ]
    
    def create(self, validated_data):
        """Custom creation logic"""
        # You can add business logic here
        # For example, automatic feedback_type based on rating
        if validated_data.get('rating'):
            rating = validated_data['rating']
            if rating >= 4:
                validated_data['feedback_type'] = 'positive'
            elif rating <= 2:
                validated_data['feedback_type'] = 'negative'
            else:
                validated_data['feedback_type'] = 'neutral'
        
        return super().create(validated_data)


class UserRecommendationSerializer(serializers.ModelSerializer):
    """
    Serializer for UserRecommendations model.
    Provides comprehensive recommendation data for API responses.
    """
    
    # Computed properties from the model
    is_fresh = serializers.ReadOnlyField()
    click_through_time = serializers.ReadOnlyField()
    relevance_score = serializers.ReadOnlyField()
    
    # Display fields for better UX
    user_username = serializers.CharField(source='user.username', read_only=True)
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    movie_genre = serializers.SerializerMethodField()
    movie_year = serializers.SerializerMethodField()
    
    class Meta:
        model = UserRecommendations
        fields = [
            'id',
            'user',
            'user_username',
            'movie',
            'movie_title',
            'movie_genre',
            'movie_year',
            'score',
            'algorithm',
            'generated_at',
            'clicked',
            'clicked_at',
            # Computed fields
            'is_fresh',
            'click_through_time',
            'relevance_score',
        ]
        read_only_fields = [
            'id',
            'generated_at',
            'user_username',
            'movie_title',
            'movie_genre',
            'movie_year',
            'is_fresh',
            'click_through_time',
            'relevance_score',
        ]
    
    def get_movie_genre(self, obj):
        """Get movie genres as a list"""
        if hasattr(obj.movie, 'genres') and obj.movie.genres.exists():
            return [genre.name for genre in obj.movie.genres.all()]
        return []
    
    def get_movie_year(self, obj):
        """Get movie release year"""
        if hasattr(obj.movie, 'release_date') and obj.movie.release_date:
            return obj.movie.release_date.year
        return None


class UserRecommendationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating recommendations.
    Used by recommendation algorithms to create new recommendations.
    """
    
    class Meta:
        model = UserRecommendations
        fields = [
            'user',
            'movie',
            'score',
            'algorithm',
        ]
    
    def validate_score(self, value):
        """Ensure score is within reasonable range"""
        if value < 0 or value > 10:
            raise serializers.ValidationError("Score must be between 0 and 10")
        return value
    
    def validate(self, data):
        """Check for duplicate recommendations"""
        user = data.get('user')
        movie = data.get('movie')
        algorithm = data.get('algorithm')
        
        # Check if recommendation already exists
        if UserRecommendations.objects.filter(
            user=user,
            movie=movie,
            algorithm=algorithm
        ).exists():
            raise serializers.ValidationError(
                "Recommendation already exists for this user-movie-algorithm combination"
            )
        
        return data


class UserPreferencesSerializer(serializers.Serializer):
    """
    Custom serializer for user preferences analysis.
    Not tied to a specific model - used for computed data.
    """
    
    user_id = serializers.IntegerField()
    preferred_genres = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    average_rating = serializers.FloatField(read_only=True)
    total_interactions = serializers.IntegerField(read_only=True)
    favorite_movies = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    recommendation_click_rate = serializers.FloatField(read_only=True)
    
    def to_representation(self, instance):
        """
        Custom representation for user preferences.
        Instance would be a user object.
        """
        if not hasattr(instance, 'id'):
            raise serializers.ValidationError("Invalid user instance")
        
        # Calculate preferences using model methods
        preferred_genres = UserMovieInteraction.get_user_preferred_genres(instance)
        
        # Get user's interactions
        interactions = UserMovieInteraction.objects.filter(user=instance)
        ratings = interactions.filter(interaction_type='rating', rating__isnull=False)
        
        # Calculate average rating
        avg_rating = ratings.aggregate(avg=serializers.models.Avg('rating'))['avg']
        
        # Get favorite movies (high ratings or likes)
        favorites = interactions.filter(
            models.Q(interaction_type='favorite') |
            models.Q(interaction_type='rating', rating__gte=4.0)
        ).select_related('movie')[:5]
        
        # Calculate recommendation click rate
        recommendations = UserRecommendations.objects.filter(user=instance)
        total_recs = recommendations.count()
        clicked_recs = recommendations.filter(clicked=True).count()
        click_rate = (clicked_recs / total_recs * 100) if total_recs > 0 else 0
        
        return {
            'user_id': instance.id,
            'preferred_genres': [genre.name for genre in preferred_genres],
            'average_rating': round(avg_rating, 2) if avg_rating else None,
            'total_interactions': interactions.count(),
            'favorite_movies': [fav.movie.title for fav in favorites],
            'recommendation_click_rate': round(click_rate, 2),
        }


class RecommendationPerformanceSerializer(serializers.Serializer):
    """
    Serializer for algorithm performance analysis.
    Used for analytics and monitoring endpoints.
    """
    
    algorithm = serializers.CharField()
    total_recommendations = serializers.IntegerField()
    clicked_recommendations = serializers.IntegerField()
    click_through_rate = serializers.FloatField()
    average_score = serializers.FloatField()
    period_days = serializers.IntegerField()
    performance_grade = serializers.SerializerMethodField()
    
    def get_performance_grade(self, obj):
        """Calculate performance grade based on CTR"""
        ctr = obj.get('click_through_rate', 0)
        
        if ctr >= 15:
            return 'A'
        elif ctr >= 10:
            return 'B'
        elif ctr >= 5:
            return 'C'
        elif ctr >= 2:
            return 'D'
        else:
            return 'F'


# === NESTED SERIALIZERS ===

class InteractionWithMovieSerializer(serializers.ModelSerializer):
    """
    Serializer that includes movie details within interaction.
    Useful for user activity feeds.
    """
    
    movie_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = UserMovieInteraction
        fields = [
            'id',
            'interaction_type',
            'rating',
            'feedback_type',
            'timestamp',
            'movie_detail',
            'is_positive_feedback',
        ]
    
    def get_movie_detail(self, obj):
        """Include basic movie information"""
        return {
            'id': obj.movie.id,
            'title': obj.movie.title,
            'poster_url': getattr(obj.movie, 'poster_url', None),
            'release_year': obj.movie.release_date.year if hasattr(obj.movie, 'release_date') and obj.movie.release_date else None,
        }


class RecommendationWithMovieSerializer(serializers.ModelSerializer):
    """
    Serializer that includes full movie details within recommendation.
    Perfect for recommendation feeds and carousels.
    """
    
    movie_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = UserRecommendations
        fields = [
            'id',
            'score',
            'algorithm',
            'generated_at',
            'clicked',
            'relevance_score',
            'is_fresh',
            'movie_detail',
        ]
    
    def get_movie_detail(self, obj):
        """Include comprehensive movie information"""
        movie = obj.movie
        return {
            'id': movie.id,
            'title': movie.title,
            'description': getattr(movie, 'description', ''),
            'poster_url': getattr(movie, 'poster_url', None),
            'trailer_url': getattr(movie, 'trailer_url', None),
            'release_date': getattr(movie, 'release_date', None),
            'duration': getattr(movie, 'duration', None),
            'genres': [genre.name for genre in movie.genres.all()] if hasattr(movie, 'genres') else [],
            'average_rating': UserMovieInteraction.get_movie_average_rating(movie),
        }