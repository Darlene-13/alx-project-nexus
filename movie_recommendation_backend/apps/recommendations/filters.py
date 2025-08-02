# recommendations/filters.py

import django_filters
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from .models import UserMovieInteraction, UserRecommendations, RecommendationExperiment

User = get_user_model()


class UserInteractionFilter(django_filters.FilterSet):
    """
    Filter set for UserMovieInteraction API endpoints.
    Provides filtering by interaction type, date ranges, ratings, etc.
    """
    
    # Date range filtering
    date_from = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    date_range = django_filters.ChoiceFilter(
        choices=[
            ('today', 'Today'),
            ('week', 'Last 7 days'),
            ('month', 'Last 30 days'),
            ('quarter', 'Last 90 days'),
        ],
        method='filter_by_date_range'
    )
    
    # Rating filtering
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    rating_max = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    has_rating = django_filters.BooleanFilter(method='filter_has_rating')
    
    # Interaction type filtering
    interaction_types = django_filters.MultipleChoiceFilter(
        field_name='interaction_type',
        choices=UserMovieInteraction.INTERACTION_TYPES
    )
    
    # Feedback filtering
    feedback_types = django_filters.MultipleChoiceFilter(
        field_name='feedback_type',
        choices=UserMovieInteraction.FEEDBACK_CHOICES
    )
    
    # Positive feedback filter
    is_positive = django_filters.BooleanFilter(method='filter_positive_feedback')
    
    # Source filtering
    sources = django_filters.MultipleChoiceFilter(
        field_name='source',
        choices=UserMovieInteraction.SOURCE_CHOICES
    )
    
    # Movie filtering
    movie_title = django_filters.CharFilter(field_name='movie__title', lookup_expr='icontains')
    movie_genre = django_filters.CharFilter(method='filter_by_movie_genre')
    movie_year = django_filters.NumberFilter(method='filter_by_movie_year')
    movie_rating_min = django_filters.NumberFilter(field_name='movie__tmdb_rating', lookup_expr='gte')
    movie_rating_max = django_filters.NumberFilter(field_name='movie__tmdb_rating', lookup_expr='lte')
    
    # Engagement filtering
    high_engagement = django_filters.BooleanFilter(method='filter_high_engagement')
    
    # User filtering (for admin use)
    user = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    username = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')
    
    class Meta:
        model = UserMovieInteraction
        fields = [
            'interaction_type', 'feedback_type', 'source',
            'date_from', 'date_to', 'date_range',
            'rating_min', 'rating_max', 'has_rating',
            'is_positive', 'high_engagement', 'movie_title',
            'movie_genre', 'movie_year', 'user', 'username'
        ]
    
    def filter_by_date_range(self, queryset, name, value):
        """Filter by predefined date ranges"""
        now = timezone.now()
        
        if value == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif value == 'week':
            start_date = now - timedelta(days=7)
        elif value == 'month':
            start_date = now - timedelta(days=30)
        elif value == 'quarter':
            start_date = now - timedelta(days=90)
        else:
            return queryset
        
        return queryset.filter(timestamp__gte=start_date)
    
    def filter_has_rating(self, queryset, name, value):
        """Filter interactions that have or don't have ratings"""
        if value:
            return queryset.filter(rating__isnull=False)
        else:
            return queryset.filter(rating__isnull=True)
    
    def filter_positive_feedback(self, queryset, name, value):
        """Filter by positive feedback indicators"""
        positive_filter = Q(
            Q(interaction_type__in=['like', 'favorite', 'watchlist']) |
            Q(feedback_type='positive') |
            Q(rating__gte=4.0)
        )
        
        if value:
            return queryset.filter(positive_filter)
        else:
            return queryset.exclude(positive_filter)
    
    def filter_by_movie_genre(self, queryset, name, value):
        """Filter by movie genre"""
        return queryset.filter(movie__genres__name__icontains=value)
    
    def filter_by_movie_year(self, queryset, name, value):
        """Filter by movie release year"""
        return queryset.filter(movie__release_date__year=value)
    
    def filter_high_engagement(self, queryset, name, value):
        """Filter by high engagement interactions"""
        if value:
            return queryset.filter(
                interaction_type__in=['like', 'favorite', 'watchlist', 'rating']
            )
        else:
            return queryset.filter(interaction_type__in=['view', 'click'])


class RecommendationFilter(django_filters.FilterSet):
    """
    Filter set for UserRecommendations API endpoints.
    Provides filtering by algorithm, scores, freshness, etc.
    """
    
    # Algorithm filtering
    algorithms = django_filters.MultipleChoiceFilter(
        field_name='algorithm',
        choices=[
            ('collaborative_filtering', 'Collaborative Filtering'),
            ('content_based', 'Content Based'),
            ('hybrid', 'Hybrid'),
            ('trending', 'Trending'),
            ('demographic', 'Demographic'),
            ('matrix_factorization', 'Matrix Factorization'),
        ]
    )
    
    # Score filtering
    score_min = django_filters.NumberFilter(field_name='score', lookup_expr='gte')
    score_max = django_filters.NumberFilter(field_name='score', lookup_expr='lte')
    high_score = django_filters.BooleanFilter(method='filter_high_score')
    
    # Date filtering
    generated_from = django_filters.DateTimeFilter(field_name='generated_at', lookup_expr='gte')
    generated_to = django_filters.DateTimeFilter(field_name='generated_at', lookup_expr='lte')
    freshness = django_filters.ChoiceFilter(
        choices=[
            ('fresh', 'Fresh (last 7 days)'),
            ('recent', 'Recent (last 30 days)'),
            ('stale', 'Stale (older than 7 days)'),
        ],
        method='filter_by_freshness'
    )
    
    # Click status filtering
    clicked_status = django_filters.ChoiceFilter(
        choices=[
            ('clicked', 'Clicked'),
            ('unclicked', 'Not Clicked'),
            ('all', 'All'),
        ],
        method='filter_by_click_status'
    )
    
    # Movie filtering
    movie_title = django_filters.CharFilter(field_name='movie__title', lookup_expr='icontains')
    movie_genre = django_filters.CharFilter(method='filter_by_movie_genre')
    movie_rating_min = django_filters.NumberFilter(field_name='movie__tmdb_rating', lookup_expr='gte')
    movie_rating_max = django_filters.NumberFilter(field_name='movie__tmdb_rating', lookup_expr='lte')
    movie_year = django_filters.NumberFilter(method='filter_by_movie_year')
    
    # User filtering (for admin use)
    user = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    username = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')
    
    # Performance filtering
    has_clicks = django_filters.BooleanFilter(method='filter_has_clicks')
    
    class Meta:
        model = UserRecommendations
        fields = [
            'algorithm', 'clicked', 'score_min', 'score_max',
            'generated_from', 'generated_to', 'freshness',
            'clicked_status', 'high_score', 'movie_title',
            'movie_genre', 'movie_year', 'user', 'username',
            'has_clicks'
        ]
    
    def filter_high_score(self, queryset, name, value):
        """Filter recommendations with high scores (>= 7.0)"""
        if value:
            return queryset.filter(score__gte=7.0)
        else:
            return queryset.filter(score__lt=7.0)
    
    def filter_by_freshness(self, queryset, name, value):
        """Filter by recommendation freshness"""
        now = timezone.now()
        
        if value == 'fresh':
            cutoff = now - timedelta(days=7)
            return queryset.filter(generated_at__gte=cutoff)
        elif value == 'recent':
            cutoff = now - timedelta(days=30)
            return queryset.filter(generated_at__gte=cutoff)
        elif value == 'stale':
            cutoff = now - timedelta(days=7)
            return queryset.filter(generated_at__lt=cutoff)
        
        return queryset
    
    def filter_by_click_status(self, queryset, name, value):
        """Filter by click status"""
        if value == 'clicked':
            return queryset.filter(clicked=True)
        elif value == 'unclicked':
            return queryset.filter(clicked=False)
        # 'all' returns unfiltered queryset
        return queryset
    
    def filter_by_movie_genre(self, queryset, name, value):
        """Filter by movie genre"""
        return queryset.filter(movie__genres__name__icontains=value)
    
    def filter_by_movie_year(self, queryset, name, value):
        """Filter by movie release year"""
        return queryset.filter(movie__release_date__year=value)
    
    def filter_has_clicks(self, queryset, name, value):
        """Filter recommendations that have been clicked"""
        if value:
            return queryset.filter(clicked=True)
        else:
            return queryset.filter(clicked=False)


class UserPreferencesFilter(django_filters.FilterSet):
    """
    Filter set for User model preferences (used in admin).
    Filters users based on recommendation preferences stored in User model.
    """
    
    # Demographics filtering (from User model)
    age_min = django_filters.NumberFilter(method='filter_age_min')
    age_max = django_filters.NumberFilter(method='filter_age_max')
    age_group = django_filters.ChoiceFilter(
        choices=[
            ('teen', 'Teen (13-17)'),
            ('young_adult', 'Young Adult (18-29)'),
            ('adult', 'Adult (30-49)'),
            ('senior', 'Senior (50+)'),
        ],
        method='filter_by_age_group'
    )
    
    # Location filtering
    country = django_filters.CharFilter(field_name='country', lookup_expr='iexact')
    countries = django_filters.MultipleChoiceFilter(
        field_name='country',
        method='filter_by_countries'
    )
    
    # Language filtering
    language = django_filters.CharFilter(field_name='preferred_language', lookup_expr='iexact')
    
    # Onboarding status filtering (from User model)
    onboarding_status = django_filters.ChoiceFilter(
        choices=[
            ('completed', 'Completed'),
            ('pending', 'Pending'),
            ('partial', 'Partial'),
        ],
        method='filter_by_onboarding_status'
    )
    
    # Preferences filtering (from User model)
    has_preferences = django_filters.BooleanFilter(method='filter_has_preferences')
    has_favorite_genres = django_filters.BooleanFilter(method='filter_has_favorite_genres')
    
    algorithm_preference = django_filters.MultipleChoiceFilter(
        field_name='algorithm_preference',
        choices=[
            ('collaborative_filtering', 'Collaborative Filtering'),
            ('content_based', 'Content Based'),
            ('hybrid', 'Hybrid'),
            ('trending', 'Trending'),
            ('demographic', 'Demographic'),
        ]
    )
    
    content_rating = django_filters.MultipleChoiceFilter(
        field_name='content_rating_preference',
        choices=[
            ('G', 'G - General Audiences'),
            ('PG', 'PG - Parental Guidance'),
            ('PG-13', 'PG-13 - Parents Strongly Cautioned'),
            ('R', 'R - Restricted'),
            ('NC-17', 'NC-17 - Adults Only'),
        ]
    )
    
    preferred_decade = django_filters.MultipleChoiceFilter(
        field_name='preferred_decade',
        choices=[
            ('1980s', '1980s'),
            ('1990s', '1990s'),
            ('2000s', '2000s'),
            ('2010s', '2010s'),
            ('2020s', '2020s'),
        ]
    )
    
    # Diversity preferences
    diversity_preference_min = django_filters.NumberFilter(
        field_name='diversity_preference', 
        lookup_expr='gte'
    )
    diversity_preference_max = django_filters.NumberFilter(
        field_name='diversity_preference', 
        lookup_expr='lte'
    )
    
    novelty_preference_min = django_filters.NumberFilter(
        field_name='novelty_preference', 
        lookup_expr='gte'
    )
    novelty_preference_max = django_filters.NumberFilter(
        field_name='novelty_preference', 
        lookup_expr='lte'
    )
    
    # Privacy filtering (from User model)
    allows_demographic_targeting = django_filters.BooleanFilter(
        field_name='allow_demographic_targeting'
    )
    has_data_consent = django_filters.BooleanFilter(field_name='data_usage_consent')
    
    # Premium status
    is_premium = django_filters.BooleanFilter(field_name='is_premium')
    
    # Date filtering
    joined_from = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='gte')
    joined_to = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='lte')
    
    # Activity filtering
    has_interactions = django_filters.BooleanFilter(method='filter_has_interactions')
    last_interaction = django_filters.DateTimeFilter(method='filter_last_interaction')
    
    class Meta:
        model = User
        fields = [
            'age_min', 'age_max', 'age_group', 'country', 'language',
            'onboarding_status', 'has_preferences', 'has_favorite_genres',
            'algorithm_preference', 'content_rating', 'preferred_decade',
            'allows_demographic_targeting', 'has_data_consent', 'is_premium',
            'joined_from', 'joined_to', 'has_interactions'
        ]
    
    def filter_age_min(self, queryset, name, value):
        """Filter by minimum age calculated from date_of_birth"""
        from datetime import date, timedelta
        if value:
            max_birth_date = date.today() - timedelta(days=value * 365)
            return queryset.filter(date_of_birth__lte=max_birth_date)
        return queryset
    
    def filter_age_max(self, queryset, name, value):
        """Filter by maximum age calculated from date_of_birth"""
        from datetime import date, timedelta
        if value:
            min_birth_date = date.today() - timedelta(days=(value + 1) * 365)
            return queryset.filter(date_of_birth__gte=min_birth_date)
        return queryset
    
    def filter_by_age_group(self, queryset, name, value):
        """Filter by age group categories using date_of_birth"""
        from datetime import date, timedelta
        today = date.today()
        
        age_ranges = {
            'teen': (13, 17),
            'young_adult': (18, 29),
            'adult': (30, 49),
            'senior': (50, 120)
        }
        
        if value in age_ranges:
            min_age, max_age = age_ranges[value]
            max_birth_date = today - timedelta(days=min_age * 365)
            min_birth_date = today - timedelta(days=(max_age + 1) * 365)
            return queryset.filter(
                date_of_birth__gte=min_birth_date,
                date_of_birth__lte=max_birth_date
            )
        
        return queryset
    
    def filter_by_countries(self, queryset, name, value):
        """Filter by multiple countries"""
        if value:
            return queryset.filter(country__in=value)
        return queryset
    
    def filter_by_onboarding_status(self, queryset, name, value):
        """Filter by onboarding completion status (User model fields)"""
        if value == 'completed':
            return queryset.filter(onboarding_completed=True)
        elif value == 'pending':
            return queryset.filter(
                onboarding_completed=False,
                cold_start_preferences_collected=False
            )
        elif value == 'partial':
            return queryset.filter(
                onboarding_completed=False,
                cold_start_preferences_collected=True
            )
        
        return queryset
    
    def filter_has_preferences(self, queryset, name, value):
        """Filter users who have set preferences (User model fields)"""
        if value:
            return queryset.exclude(favorite_genres=[]).exclude(
                content_rating_preference__isnull=True,
                preferred_decade__isnull=True
            )
        else:
            return queryset.filter(
                favorite_genres=[],
                content_rating_preference__isnull=True,
                preferred_decade__isnull=True
            )
    
    def filter_has_favorite_genres(self, queryset, name, value):
        """Filter users who have set favorite genres"""
        if value:
            return queryset.exclude(favorite_genres=[])
        else:
            return queryset.filter(favorite_genres=[])
    
    def filter_has_interactions(self, queryset, name, value):
        """Filter users who have movie interactions"""
        if value:
            return queryset.filter(movie_interactions__isnull=False).distinct()
        else:
            return queryset.filter(movie_interactions__isnull=True)
    
    def filter_last_interaction(self, queryset, name, value):
        """Filter users by their last interaction date"""
        return queryset.filter(
            movie_interactions__timestamp__gte=value
        ).distinct()


class RecommendationExperimentFilter(django_filters.FilterSet):
    """
    Filter set for RecommendationExperiment admin interface.
    Provides filtering by status, algorithms, dates, and performance.
    """
    
    # Status filtering
    status = django_filters.ChoiceFilter(
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('scheduled', 'Scheduled'),
            ('stopped', 'Stopped'),
        ],
        method='filter_by_status'
    )
    
    # Algorithm filtering
    algorithm_a = django_filters.ChoiceFilter(
        field_name='algorithm_a',
        choices=[
            ('collaborative', 'Collaborative Filtering'),
            ('content_based', 'Content-Based Filtering'),
            ('hybrid', 'Hybrid Algorithm'),
            ('trending', 'Trending Movies'),
            ('demographic', 'Demographic-Based'),
            ('matrix_factorization', 'Matrix Factorization'),
        ]
    )
    
    algorithm_b = django_filters.ChoiceFilter(
        field_name='algorithm_b',
        choices=[
            ('collaborative', 'Collaborative Filtering'),
            ('content_based', 'Content-Based Filtering'),
            ('hybrid', 'Hybrid Algorithm'),
            ('trending', 'Trending Movies'),
            ('demographic', 'Demographic-Based'),
            ('matrix_factorization', 'Matrix Factorization'),
        ]
    )
    
    # Date filtering
    start_date_from = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_date_to = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    end_date_from = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='gte')
    end_date_to = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='lte')
    
    # Results filtering
    has_results = django_filters.BooleanFilter(method='filter_has_results')
    is_significant = django_filters.BooleanFilter(method='filter_is_significant')
    
    # Creator filtering
    created_by = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    creator_username = django_filters.CharFilter(field_name='created_by__username', lookup_expr='icontains')
    
    # Target metric filtering
    target_metric = django_filters.ChoiceFilter(
        field_name='target_metric',
        choices=[
            ('ctr', 'Click-Through Rate'),
            ('engagement', 'User Engagement'),
            ('retention', 'User Retention'),
            ('conversion', 'Conversion Rate'),
            ('rating', 'Average Rating'),
            ('time_spent', 'Time Spent on Platform'),
        ]
    )
    
    class Meta:
        model = RecommendationExperiment
        fields = [
            'status', 'algorithm_a', 'algorithm_b', 'target_metric',
            'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to',
            'has_results', 'is_significant', 'created_by', 'creator_username'
        ]
    
    def filter_by_status(self, queryset, name, value):
        """Filter experiments by their current status"""
        now = timezone.now()
        
        if value == 'active':
            return queryset.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            )
        elif value == 'completed':
            return queryset.filter(end_date__lt=now)
        elif value == 'scheduled':
            return queryset.filter(
                is_active=True,
                start_date__gt=now
            )
        elif value == 'stopped':
            return queryset.filter(is_active=False)
        
        return queryset
    
    def filter_has_results(self, queryset, name, value):
        """Filter experiments that have statistical results"""
        if value:
            return queryset.filter(p_value__isnull=False)
        else:
            return queryset.filter(p_value__isnull=True)
    
    def filter_is_significant(self, queryset, name, value):
        """Filter experiments with statistically significant results"""
        if value:
            return queryset.filter(
                p_value__isnull=False,
                winner_algorithm__isnull=False
            )
        else:
            return queryset.filter(
                Q(p_value__isnull=True) | Q(winner_algorithm__isnull=True)
            )