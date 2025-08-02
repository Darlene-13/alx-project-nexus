# recommendations/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from datetime import timedelta
import json

from .models import (
    UserMovieInteraction, 
    UserRecommendations, 
    RecommendationExperiment
)

User = get_user_model()

# BASE SERIALIZERS & MIXINS

class TimestampMixin(serializers.ModelSerializer):
    """Mixin for consistent timestamp formatting"""
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    updated_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')


class ReadOnlyModelSerializer(serializers.ModelSerializer):
    """Base serializer for read-only models"""
    def create(self, validated_data):
        raise serializers.ValidationError("Creation not allowed through this endpoint")
    
    def update(self, instance, validated_data):
        raise serializers.ValidationError("Updates not allowed through this endpoint")

# USER MOVIE INTERACTION SERIALIZERS

class UserMovieInteractionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing interactions.
    Used in list views and nested relationships.
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    movie_poster = serializers.CharField(source='movie.poster_path', read_only=True)
    
    # Computed fields (read-only)
    is_recent = serializers.BooleanField(read_only=True)
    is_positive_feedback = serializers.BooleanField(read_only=True)
    engagement_weight = serializers.FloatField(read_only=True)

    class Meta:
        model = UserMovieInteraction
        fields = [
            'id', 'user_username', 'movie_title', 'movie_poster',
            'interaction_type', 'rating', 'feedback_type',
            'source', 'timestamp', 'is_recent', 'is_positive_feedback',
            'engagement_weight'
        ]
        read_only_fields = [
            'id', 'user_username', 'movie_title', 'movie_poster',
            'timestamp', 'is_recent', 'is_positive_feedback', 'engagement_weight'
        ]


class UserMovieInteractionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for creating and viewing individual interactions.
    Includes full validation and nested data.
    """
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    movie = serializers.PrimaryKeyRelatedField(queryset=None)  # Set in view
    
    # Computed fields (read-only)
    is_recent = serializers.BooleanField(read_only=True)
    is_positive_feedback = serializers.BooleanField(read_only=True)
    engagement_weight = serializers.FloatField(read_only=True)
    
    # Nested movie data for responses
    movie_data = serializers.SerializerMethodField()

    class Meta:
        model = UserMovieInteraction
        fields = [
            'id', 'user', 'movie', 'interaction_type', 'rating',
            'feedback_type', 'feedback_comment', 'metadata', 'source',
            'timestamp', 'is_recent', 'is_positive_feedback', 
            'engagement_weight', 'movie_data'
        ]
        read_only_fields = [
            'id', 'user', 'timestamp', 'is_recent', 
            'is_positive_feedback', 'engagement_weight', 'movie_data'
        ]

    def get_movie_data(self, obj):
        """Get basic movie information for the response"""
        if obj.movie:
            return {
                'id': obj.movie.id,
                'title': obj.movie.title,
                'poster_path': obj.movie.poster_path,
                'release_date': obj.movie.release_date,
                'tmdb_rating': obj.movie.tmdb_rating
            }
        return None

    def validate(self, data):
        """Custom validation for interaction creation"""
        interaction_type = data.get('interaction_type')
        rating = data.get('rating')
        
        # Validate rating is provided for rating interactions
        if interaction_type == 'rating' and rating is None:
            raise serializers.ValidationError(
                "Rating is required when interaction_type is 'rating'"
            )
        
        # Validate rating is not provided for non-rating interactions
        if interaction_type != 'rating' and rating is not None:
            raise serializers.ValidationError(
                "Rating should only be provided when interaction_type is 'rating'"
            )
        
        return data

    def create(self, validated_data):
        """Create interaction with current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserMovieInteractionCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for quick interaction creation.
    Used for high-frequency interactions like views and clicks.
    """
    class Meta:
        model = UserMovieInteraction
        fields = ['movie', 'interaction_type', 'rating', 'source', 'metadata']

    def validate(self, data):
        """Quick validation for interaction creation"""
        interaction_type = data.get('interaction_type')
        rating = data.get('rating')
        
        if interaction_type == 'rating' and rating is None:
            raise serializers.ValidationError("Rating required for rating interactions")
        
        return data

    def create(self, validated_data):
        """Create interaction with current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# USER RECOMMENDATIONS SERIALIZERS

class UserRecommendationListSerializer(ReadOnlyModelSerializer):
    """
    Lightweight serializer for recommendation lists.
    Optimized for performance in recommendation feeds.
    """
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    movie_poster = serializers.CharField(source='movie.poster_path', read_only=True)
    movie_rating = serializers.DecimalField(
        source='movie.tmdb_rating', 
        max_digits=3, 
        decimal_places=1, 
        read_only=True
    )
    
    # Computed fields
    is_fresh = serializers.BooleanField(read_only=True)
    relevance_score = serializers.FloatField(read_only=True)

    class Meta:
        model = UserRecommendations
        fields = [
            'id', 'movie', 'movie_title', 'movie_poster', 'movie_rating',
            'score', 'algorithm', 'generated_at', 'is_fresh', 'relevance_score'
        ]


class UserRecommendationDetailSerializer(ReadOnlyModelSerializer, TimestampMixin):
    """
    Detailed serializer for individual recommendations.
    Includes full movie data and performance metrics.
    """
    movie_data = serializers.SerializerMethodField()
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    # Computed fields
    is_fresh = serializers.BooleanField(read_only=True)
    relevance_score = serializers.FloatField(read_only=True)
    click_through_time = serializers.SerializerMethodField()

    class Meta:
        model = UserRecommendations
        fields = [
            'id', 'user', 'user_username', 'movie', 'movie_data',
            'score', 'algorithm', 'generated_at', 'clicked', 'clicked_at',
            'is_fresh', 'relevance_score', 'click_through_time'
        ]
        read_only_fields = ['__all__']

    def get_movie_data(self, obj):
        """Get comprehensive movie information"""
        if obj.movie:
            return {
                'id': obj.movie.id,
                'title': obj.movie.title,
                'overview': obj.movie.overview,
                'poster_path': obj.movie.poster_path,
                'backdrop_path': obj.movie.backdrop_path,
                'release_date': obj.movie.release_date,
                'runtime': obj.movie.runtime,
                'tmdb_rating': obj.movie.tmdb_rating,
                'director': obj.movie.director,
                'genres': [genre.name for genre in obj.movie.genres.all()] if hasattr(obj.movie, 'genres') else []
            }
        return None

    def get_click_through_time(self, obj):
        """Get formatted click-through time"""
        ctt = obj.click_through_time
        if ctt:
            total_seconds = int(ctt.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None


class RecommendationClickSerializer(serializers.Serializer):
    """
    Serializer for marking recommendations as clicked.
    Used in PATCH/POST endpoints for tracking user interactions.
    """
    recommendation_id = serializers.IntegerField()
    clicked_at = serializers.DateTimeField(default=timezone.now)

    def validate_recommendation_id(self, value):
        """Validate recommendation exists and belongs to current user"""
        try:
            recommendation = UserRecommendations.objects.get(
                id=value,
                user=self.context['request'].user
            )
            return value
        except UserRecommendations.DoesNotExist:
            raise serializers.ValidationError("Recommendation not found")

    def save(self):
        """Mark recommendation as clicked"""
        recommendation = UserRecommendations.objects.get(
            id=self.validated_data['recommendation_id']
        )
        recommendation.mark_as_clicked()
        return recommendation
# RECOMMENDATION EXPERIMENT SERIALIZERS

class RecommendationExperimentListSerializer(serializers.ModelSerializer):
    """
    Public serializer for listing experiments.
    Limited information for non-admin users.
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    # Computed fields
    is_running = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = RecommendationExperiment
        fields = [
            'id', 'name', 'description', 'algorithm_a', 'algorithm_b',
            'start_date', 'end_date', 'is_active', 'target_metric',
            'created_by_username', 'is_running', 'is_completed',
            'duration_days', 'progress_percentage'
        ]
        read_only_fields = ['__all__']


class RecommendationExperimentDetailSerializer(serializers.ModelSerializer, TimestampMixin):
    """
    Admin serializer for managing experiments.
    Full access to all fields and statistical results.
    """
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    # Computed fields
    is_running = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    has_significant_result = serializers.BooleanField(read_only=True)
    
    # Experiment metrics
    current_metrics = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationExperiment
        fields = [
            'id', 'name', 'description', 'algorithm_a', 'algorithm_b',
            'traffic_split', 'start_date', 'end_date', 'is_active',
            'target_metric', 'minimum_sample_size', 'confidence_level',
            'statistical_significance', 'winner_algorithm', 'p_value',
            'effect_size', 'created_by', 'created_by_username',
            'created_at', 'updated_at', 'is_running', 'is_completed',
            'duration_days', 'progress_percentage', 'has_significant_result',
            'current_metrics'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_username', 'created_at', 
            'updated_at', 'is_running', 'is_completed', 'duration_days',
            'progress_percentage', 'has_significant_result', 'statistical_significance',
            'winner_algorithm', 'p_value', 'effect_size', 'current_metrics'
        ]

    def get_current_metrics(self, obj):
        """Get current experiment performance metrics"""
        try:
            return obj.calculate_metrics()
        except Exception:
            return None

    def validate(self, data):
        """Validate experiment configuration"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        algorithm_a = data.get('algorithm_a')
        algorithm_b = data.get('algorithm_b')
        
        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError("End date must be after start date")
        
        if algorithm_a and algorithm_b and algorithm_a == algorithm_b:
            raise serializers.ValidationError("Algorithm A and Algorithm B must be different")
        
        return data

    def create(self, validated_data):
        """Create experiment with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class ExperimentResultsSerializer(serializers.Serializer):
    """
    Serializer for updating experiment statistical results.
    Used by analytics jobs to update experiment outcomes.
    """
    p_value = serializers.FloatField(min_value=0.0, max_value=1.0)
    effect_size = serializers.FloatField()
    winner_algorithm = serializers.ChoiceField(
        choices=RecommendationExperiment.ALGORITHM_CHOICES,
        allow_null=True,
        required=False
    )

    def save(self, experiment):
        """Update experiment with statistical results"""
        experiment.update_statistical_results(
            p_value=self.validated_data['p_value'],
            effect_size=self.validated_data['effect_size'],
            winner=self.validated_data.get('winner_algorithm')
        )
        return experiment

# USER PROFILE SERIALIZERS (Working with User Model)

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data stored in User model.
    Handles recommendation-specific preferences and demographics.
    """
    # Read-only computed fields
    age = serializers.SerializerMethodField()
    age_group = serializers.SerializerMethodField()
    is_new_user = serializers.SerializerMethodField()
    cold_start_strategy = serializers.SerializerMethodField()
    has_preferences = serializers.SerializerMethodField()
    
    # Basic user info (read-only)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)

    class Meta:
        model = User
        fields = [
            # Basic user info
            'id', 'username', 'email',
            
            # Demographics (from User model)
            'date_of_birth', 'country', 'preferred_language', 'timezone',
            
            # Recommendation preferences (from User model)
            'favorite_genres', 'algorithm_preference', 'diversity_preference',
            'novelty_preference', 'content_rating_preference', 'preferred_decade',
            
            # Onboarding tracking (from User model)
            'onboarding_completed', 'onboarding_completed_at', 
            'cold_start_preferences_collected',
            
            # Privacy settings (from User model)
            'allow_demographic_targeting', 'data_usage_consent',
            
            # Computed fields
            'age', 'age_group', 'is_new_user', 'cold_start_strategy', 'has_preferences',
            
            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'onboarding_completed_at',
            'age', 'age_group', 'is_new_user', 'cold_start_strategy', 'has_preferences',
            'created_at', 'updated_at'
        ]

    def get_age(self, obj):
        """Calculate age from date_of_birth"""
        if obj.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - obj.date_of_birth.year
            if today.month < obj.date_of_birth.month or (today.month == obj.date_of_birth.month and today.day < obj.date_of_birth.day):
                age -= 1
            return age
        return None

    def get_age_group(self, obj):
        """Get user's age group"""
        age = self.get_age(obj)
        if not age:
            return None
        if age < 18:
            return 'teen'
        elif age < 30:
            return 'young_adult'
        elif age < 50:
            return 'adult'
        else:
            return 'senior'

    def get_is_new_user(self, obj):
        """Check if user needs onboarding"""
        return not getattr(obj, 'onboarding_completed', False) and not getattr(obj, 'cold_start_preferences_collected', False)

    def get_cold_start_strategy(self, obj):
        """Determine cold start strategy"""
        age = self.get_age(obj)
        country = getattr(obj, 'country', '')
        favorite_genres = getattr(obj, 'favorite_genres', [])
        
        if age and country:
            return 'demographic'
        elif favorite_genres:
            return 'content_based'
        else:
            return 'popular'

    def get_has_preferences(self, obj):
        """Check if user has set preferences"""
        favorite_genres = getattr(obj, 'favorite_genres', [])
        content_rating = getattr(obj, 'content_rating_preference', None)
        preferred_decade = getattr(obj, 'preferred_decade', None)
        
        return bool(favorite_genres) or content_rating is not None or preferred_decade is not None

    def validate_favorite_genres(self, value):
        """Validate favorite_genres JSON format"""
        if not isinstance(value, list):
            raise serializers.ValidationError("favorite_genres must be a list")
        
        for genre_item in value:
            if isinstance(genre_item, dict):
                if 'genre_id' not in genre_item:
                    raise serializers.ValidationError("Each genre must have 'genre_id'")
                if 'weight' in genre_item:
                    weight = genre_item['weight']
                    if not isinstance(weight, (int, float)) or not (0.0 <= weight <= 1.0):
                        raise serializers.ValidationError("Genre weight must be between 0.0 and 1.0")
            elif not isinstance(genre_item, int):
                raise serializers.ValidationError(
                    "Genre items must be integers (genre IDs) or objects with genre_id and weight"
                )
        
        return value


class UserOnboardingSerializer(serializers.ModelSerializer):
    """
    Specialized serializer for onboarding process.
    Captures initial user preferences for cold start recommendations.
    """
    class Meta:
        model = User
        fields = [
            'date_of_birth', 'country', 'favorite_genres',
            'content_rating_preference', 'preferred_decade',
            'diversity_preference', 'novelty_preference',
            'allow_demographic_targeting', 'data_usage_consent'
        ]

    def save(self, **kwargs):
        """Save profile and mark onboarding as completed"""
        instance = super().save(**kwargs)
        instance.onboarding_completed = True
        instance.onboarding_completed_at = timezone.now()
        instance.cold_start_preferences_collected = True
        instance.save(update_fields=['onboarding_completed', 'onboarding_completed_at', 'cold_start_preferences_collected'])
        return instance


class GenrePreferenceSerializer(serializers.Serializer):
    """
    Serializer for adding/removing genre preferences.
    Used in dedicated endpoints for genre management.
    """
    genre_id = serializers.IntegerField()
    weight = serializers.FloatField(default=1.0, min_value=0.0, max_value=1.0)
    action = serializers.ChoiceField(choices=['add', 'remove'], default='add')

    def validate_genre_id(self, value):
        """Validate genre exists"""
        from apps.movies.models import Genre
        try:
            Genre.objects.get(id=value)
            return value
        except Genre.DoesNotExist:
            raise serializers.ValidationError("Genre not found")

    def save(self, user):
        """Add or remove genre preference"""
        genre_id = self.validated_data['genre_id']
        weight = self.validated_data['weight']
        action = self.validated_data['action']
        
        favorite_genres = user.favorite_genres or []
        
        if action == 'add':
            # Remove existing preference for this genre
            favorite_genres = [
                genre for genre in favorite_genres 
                if (isinstance(genre, dict) and genre.get('genre_id') != genre_id) or 
                   (isinstance(genre, int) and genre != genre_id)
            ]
            
            # Add new preference
            favorite_genres.append({
                'genre_id': genre_id,
                'weight': weight
            })
            
        else:  # remove
            favorite_genres = [
                genre for genre in favorite_genres 
                if (isinstance(genre, dict) and genre.get('genre_id') != genre_id) or 
                   (isinstance(genre, int) and genre != genre_id)
            ]
        
        user.favorite_genres = favorite_genres
        user.save(update_fields=['favorite_genres'])
        return user

# ANALYTICS & REPORTING SERIALIZERS

class RecommendationPerformanceSerializer(serializers.Serializer):
    """
    Serializer for recommendation performance analytics.
    Used in dashboard and reporting endpoints.
    """
    algorithm = serializers.CharField()
    total_recommendations = serializers.IntegerField()
    clicked_recommendations = serializers.IntegerField()
    click_through_rate = serializers.FloatField()
    average_score = serializers.FloatField()
    period_days = serializers.IntegerField()


class UserInteractionSummarySerializer(serializers.Serializer):
    """
    Serializer for user interaction analytics.
    Provides summary statistics for user behavior.
    """
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_interactions = serializers.IntegerField()
    positive_interactions = serializers.IntegerField()
    average_rating = serializers.FloatField()
    preferred_genres = serializers.ListField(child=serializers.CharField())
    engagement_score = serializers.FloatField()
    last_interaction = serializers.DateTimeField()


class RecommendationContextSerializer(serializers.Serializer):
    """
    Serializer for recommendation context data.
    Used by ML algorithms to generate recommendations.
    """
    user_id = serializers.IntegerField()
    age = serializers.IntegerField(allow_null=True)
    age_group = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    favorite_genres = serializers.ListField()
    algorithm_preference = serializers.CharField(allow_null=True)
    diversity_preference = serializers.FloatField()
    novelty_preference = serializers.FloatField()
    cold_start_strategy = serializers.CharField()
    is_new_user = serializers.BooleanField()

# BULK OPERATIONS SERIALIZERS
class BulkRecommendationCreateSerializer(serializers.Serializer):
    """
    Serializer for creating multiple recommendations at once.
    Used by recommendation generation jobs.
    """
    user_id = serializers.IntegerField()
    movie_ids = serializers.ListField(child=serializers.IntegerField())
    scores = serializers.ListField(child=serializers.FloatField())
    algorithm = serializers.CharField()

    def validate(self, data):
        """Validate that lists have same length"""
        movie_ids = data.get('movie_ids', [])
        scores = data.get('scores', [])
        
        if len(movie_ids) != len(scores):
            raise serializers.ValidationError("movie_ids and scores must have the same length")
        
        return data

    def create(self, validated_data):
        """Create multiple recommendations efficiently"""
        user_id = validated_data['user_id']
        movie_ids = validated_data['movie_ids']
        scores = validated_data['scores']
        algorithm = validated_data['algorithm']
        
        recommendations = []
        for movie_id, score in zip(movie_ids, scores):
            recommendations.append(UserRecommendations(
                user_id=user_id,
                movie_id=movie_id,
                score=score,
                algorithm=algorithm
            ))
        
        # Bulk create for performance
        return UserRecommendations.objects.bulk_create(
            recommendations,
            ignore_conflicts=True  # Ignore duplicates based on unique constraint
        )