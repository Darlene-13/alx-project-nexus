"""
TThis file contains the views for the movie recommendation backend.
It includes endpoints for user interactions, recommendations, experiments, and analytics.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Avg, Q, F, Prefetch
from django.core.cache import cache
from django.conf import settings
from datetime import timedelta
import logging
from django.shortcuts import render

from .models import (
    UserMovieInteraction,
    UserRecommendations, 
    RecommendationExperiment
)
from .serializers import (
    # User Movie Interactions
    UserMovieInteractionListSerializer,
    UserMovieInteractionDetailSerializer,
    UserMovieInteractionCreateSerializer,
    
    # User Recommendations
    UserRecommendationListSerializer,
    UserRecommendationDetailSerializer,
    
    # Experiments
    RecommendationExperimentListSerializer,
    RecommendationExperimentDetailSerializer,
    ExperimentResultsSerializer,
    
    # User Profiles (now working with User model)
    UserProfileSerializer,
    UserOnboardingSerializer,
    GenrePreferenceSerializer,
    
    # Analytics
    RecommendationContextSerializer,
)

from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly
from .filters import UserInteractionFilter, RecommendationFilter, UserPreferencesFilter

User = get_user_model()
logger = logging.getLogger(__name__)

def recommendations_hub(request):
    """
    Recommendation system hub view.
    Lists all major endpoints for personalization, experiments, analytics, and utilities.
    
    Endpoint: GET /recommendations/hub/
    Example: curl -X GET "http://localhost:8000/recommendations/hub/"
    """

    endpoints_by_section = {
        "👤 USER PROFILES & PREFERENCES": [
            {"method": "GET", "url": "/recommendations/v1/users/me/", "description": "Get current user's profile", "status": "✅ Active"},
            {"method": "PATCH", "url": "/recommendations/v1/users/update_preferences/", "description": "Update preferences", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/users/onboarding/", "description": "Complete onboarding", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/users/add_genre_preference/", "description": "Add genre preference", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/users/recommendation_context/", "description": "Get recommendation context", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/users/reset_preferences/", "description": "Reset all preferences", "status": "✅ Active"},
        ],
        "🎬 USER MOVIE INTERACTIONS": [
            {"method": "GET", "url": "/recommendations/v1/interactions/", "description": "List all interactions", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/interactions/", "description": "Create a new interaction", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/interactions/{id}/", "description": "Get interaction details", "status": "✅ Active"},
            {"method": "PUT", "url": "/recommendations/v1/interactions/{id}/", "description": "Update interaction", "status": "✅ Active"},
            {"method": "PATCH", "url": "/recommendations/v1/interactions/{id}/", "description": "Partial update", "status": "✅ Active"},
            {"method": "DELETE", "url": "/recommendations/v1/interactions/{id}/", "description": "Delete interaction", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/interactions/my_interactions/", "description": "My interaction summary", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/interactions/bulk_create/", "description": "Bulk create interactions", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/interactions/analytics/", "description": "Interaction analytics", "status": "✅ Active"},
            {"method": "PATCH", "url": "/recommendations/v1/interactions/{id}/update_feedback/", "description": "Update feedback for interaction", "status": "✅ Active"},
        ],
        "🔮 RECOMMENDATIONS": [
            {"method": "GET", "url": "/recommendations/v1/recommendations/", "description": "List personalized recommendations", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/recommendations/{id}/", "description": "Get recommendation details", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/recommendations/personalized/", "description": "Get personalized (filtered)", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/recommendations/performance/", "description": "Get recommendation performance", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/recommendations/{id}/click/", "description": "Mark recommendation as clicked", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/recommendations/bulk_click/", "description": "Bulk click tracking", "status": "✅ Active"},
        ],
        "🧪 EXPERIMENTS (Admin)": [
            {"method": "GET", "url": "/recommendations/v1/experiments/", "description": "List experiments", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/experiments/", "description": "Create experiment", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/experiments/{id}/", "description": "Get experiment details", "status": "✅ Active"},
            {"method": "PUT", "url": "/recommendations/v1/experiments/{id}/", "description": "Update experiment", "status": "✅ Active"},
            {"method": "PATCH", "url": "/recommendations/v1/experiments/{id}/", "description": "Partial update", "status": "✅ Active"},
            {"method": "DELETE", "url": "/recommendations/v1/experiments/{id}/", "description": "Delete experiment", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/experiments/active/", "description": "Get active experiment", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/experiments/{id}/stop/", "description": "Stop an experiment", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/experiments/{id}/metrics/", "description": "Get experiment metrics", "status": "✅ Active"},
            {"method": "POST", "url": "/recommendations/v1/experiments/{id}/update_results/", "description": "Update experiment results", "status": "✅ Active"},
        ],
        "📊 ANALYTICS & SEGMENTATION (Admin)": [
            {"method": "GET", "url": "/recommendations/v1/analytics/dashboard/", "description": "Dashboard metrics", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/analytics/algorithm_performance/", "description": "Algorithm performance", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/analytics/user_segmentation/", "description": "User segmentation", "status": "✅ Active"},
        ],
        "🛠 UTILITY & HEALTH": [
            {"method": "POST", "url": "/recommendations/v1/utils/generate_recommendations/", "description": "Trigger generation", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/v1/utils/health/", "description": "System health check", "status": "✅ Active"},
        ],
        "📘 API DOCUMENTATION": [
            {"method": "GET", "url": "/recommendations/docs/", "description": "Swagger UI", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/redoc/", "description": "ReDoc UI", "status": "✅ Active"},
            {"method": "GET", "url": "/recommendations/schema/", "description": "Schema (JSON)", "status": "✅ Active"},
        ]
    }
    
    # Flatten the endpoints for the template
    flat_endpoints = []
    for section_name, section_endpoints in endpoints_by_section.items():
        for endpoint in section_endpoints:
            flat_endpoints.append(endpoint)
    
    context = {
        'endpoints': flat_endpoints,
        'endpoints_by_section': endpoints_by_section,  # In case you want to group them later
    }

    return render(request, 'recommendations/recommendations_hub.html', context)

# BASE CLASSES & MIXINS

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination configuration"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """Pagination for analytics and reporting"""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class CacheableViewMixin:
    """Mixin for views that can use caching"""
    cache_timeout = getattr(settings, 'RECOMMENDATION_CACHE_TIMEOUT', 300)  # 5 minutes
    
    def get_cache_key(self, prefix, *args):
        """Generate cache key"""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    def get_cached_data(self, cache_key):
        """Get data from cache"""
        return cache.get(cache_key)
    
    def set_cached_data(self, cache_key, data, timeout=None):
        """Set data in cache"""
        if timeout is None:
            timeout = self.cache_timeout
        cache.set(cache_key, data, timeout)

class UserContextMixin:
    """
    Enhanced mixin to filter queries by current user with flexible configuration.
    
    Configuration Options:
    - user_field: Field name to filter by (default: 'user')
    - allow_anonymous: Whether anonymous users can access data (default: False)
    
    Usage Examples:
    
    # Basic usage (private user data):
    class UserMovieInteractionViewSet(UserContextMixin, ModelViewSet):
        pass
    
    # Custom user field:
    class UserPostsViewSet(UserContextMixin, ModelViewSet):
        user_field = 'author'
    
    # Public data with optional user filtering:
    class PublicMoviesViewSet(UserContextMixin, ModelViewSet):
        allow_anonymous = True
    """
    
    # Configuration options - override in your viewset
    user_field = 'user'  # Field name to filter by
    allow_anonymous = False  # Whether anonymous users can access data
    
    def get_queryset(self):
        """Filter queryset to current user's data based on configuration"""
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return super().get_queryset().none()
        
        queryset = super().get_queryset()
        
        # Check if model has the specified user field
        if self._model_has_user_field():
            if self.request.user.is_authenticated:
                # Filter by authenticated user
                filter_kwargs = {self.user_field: self.request.user}
                return queryset.filter(**filter_kwargs)
            elif not self.allow_anonymous:
                # Return empty queryset for anonymous users (default behavior)
                return queryset.none()
            # If allow_anonymous=True, fall through to return unfiltered queryset
        
        return queryset
    
    def _model_has_user_field(self):
        """Check if the model has the specified user field"""
        try:
            # Check if field exists on model
            field_names = [f.name for f in self.model._meta.get_fields()]
            return self.user_field in field_names
        except AttributeError:
            # Handle case where model might not be set
            return False
    
    def perform_create(self, serializer):
        """Automatically set user when creating objects"""
        if (self.request.user.is_authenticated and 
            self._model_has_user_field() and
            self.user_field not in serializer.validated_data):
            # Only set user if:
            # 1. User is authenticated
            # 2. Model has the user field  
            # 3. User field not already set in validated_data
            serializer.save(**{self.user_field: self.request.user})
        else:
            super().perform_create(serializer)
    
    def perform_update(self, serializer):
        """Ensure user field doesn't get changed during updates"""
        # Remove user field from validated_data to prevent tampering
        validated_data = serializer.validated_data
        if self.user_field in validated_data:
            validated_data.pop(self.user_field)
        
        super().perform_update(serializer)
    
    def get_permissions(self):
        """Default permissions - can be overridden"""
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return []
        
        # You can override this in your viewset for custom permissions
        return super().get_permissions()


class PerformanceOptimizedMixin:
    """Mixin for query optimization"""
    
    def get_queryset(self):
        """Optimize queries with select_related and prefetch_related"""
        queryset = super().get_queryset()
        
        # Add select_related for foreign keys
        if hasattr(self, 'select_related_fields'):
            queryset = queryset.select_related(*self.select_related_fields)
        
        # Add prefetch_related for many-to-many relationships
        if hasattr(self, 'prefetch_related_fields'):
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        
        return queryset


# USER MOVIE INTERACTION VIEWS

class UserMovieInteractionViewSet(
    UserContextMixin, 
    PerformanceOptimizedMixin,
    CacheableViewMixin,
    viewsets.ModelViewSet
):
    
    model = UserMovieInteraction
    serializer_class = UserMovieInteractionListSerializer
    queryset = UserMovieInteraction.objects.all()
    """
    ViewSet for managing user-movie interactions.
    
    Provides CRUD operations, analytics, and bulk operations for user interactions.
    Users can only access their own interactions.
    
    Base URL: /recommendations/v1/interactions/
    """
    queryset = UserMovieInteraction.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserInteractionFilter
    search_fields = ['movie__title', 'movie__original_title', 'feedback_comment']
    ordering_fields = ['timestamp', 'rating']
    ordering = ['-timestamp']
    
    # Performance optimization
    select_related_fields = ['user', 'movie']
    prefetch_related_fields = ['movie__genres']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return UserMovieInteractionListSerializer
        elif self.action == 'create':
            return UserMovieInteractionCreateSerializer
        else:
            return UserMovieInteractionDetailSerializer

    def get_queryset(self):
        """Optimize queryset with annotations"""
        queryset = super().get_queryset()
        
        # Add computed annotations for better performance
        queryset = queryset.annotate(
            is_positive_computed=Q(
                Q(interaction_type__in=['like', 'favorite', 'watchlist']) |
                Q(feedback_type='positive') |
                Q(rating__gte=4.0)
            )
        )
        
        return queryset

    def list(self, request, *args, **kwargs):
        """
        List user's movie interactions
        
        Endpoint: GET /recommendations/v1/interactions/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/interactions/?page=1&page_size=10"
        
        Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - interaction_type: Filter by type (like, dislike, watchlist, etc.)
        - rating: Filter by rating
        - ordering: Sort by field (-timestamp, rating, etc.)
        """
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Create a new movie interaction
        
        Endpoint: POST /recommendations/v1/interactions/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/interactions/" \
        -d '{"movie": 123, "interaction_type": "like", "rating": 4.5}'
        """
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Get interaction details
        
        Endpoint: GET /recommendations/v1/interactions/{id}/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/interactions/456/"
        """
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Set user when creating interaction"""
        # Check if user already has this interaction type for this movie
        existing = UserMovieInteraction.objects.filter(
            user=self.request.user,
            movie=serializer.validated_data['movie'],
            interaction_type=serializer.validated_data['interaction_type']
        ).first()
        
        if existing:
            # Update existing interaction instead of creating duplicate
            for attr, value in serializer.validated_data.items():
                setattr(existing, attr, value)
            existing.save()
            serializer.instance = existing
        else:
            serializer.save(user=self.request.user)
        
        # Clear user's recommendation cache
        self._clear_user_cache()

    def _clear_user_cache(self):
        """Clear cached data for the current user"""
        user_id = self.request.user.id
        cache_keys = [
            f'user_recommendations:{user_id}',
            f'user_preferences:{user_id}',
            f'user_interactions_summary:{user_id}'
        ]
        cache.delete_many(cache_keys)

    @action(detail=False, methods=['get'])
    def my_interactions(self, request):
        """
        Get current user's interactions with summary stats
        
        Endpoint: GET /recommendations/v1/interactions/my_interactions/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/interactions/my_interactions/"
        
        Returns:
        - Statistics (total, positive interactions, avg rating)
        - Recent interactions (last 10)
        - Preferred genres based on interactions
        """
        cache_key = self.get_cache_key('user_interactions_summary', request.user.id)
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        queryset = self.get_queryset()

        stats = queryset.aggregate(
            total_interactions=Count('id'),
            positive_interactions=Count('id', filter=Q(is_positive_computed=True)),
            average_rating=Avg('rating'),
            total_engagement=Count('id', filter=Q(
                Q(interaction_type__in=['favorite', 'watchlist', 'like']) |  # High engagement types
                Q(rating__gte=4.0)  # High ratings
            ))
)
        
        # Calculate summary statistics
        stats = queryset.aggregate(
            total_interactions=Count('id'),
            positive_interactions=Count('id', filter=Q(is_positive_computed=True)),
            average_rating=Avg('rating'),
            total_engagement=Count('id', filter=Q(rating__isnull=False))  # Count interactions with ratings
        )
        
        # Get recent interactions
        recent_interactions = UserMovieInteractionListSerializer(
            queryset[:10], many=True, context={'request': request}
        ).data
        
        # Get preferred genres
        preferred_genres = UserMovieInteraction.get_user_preferred_genres(request.user)
        
        response_data = {
            'statistics': stats,
            'recent_interactions': recent_interactions,
            'preferred_genres': [{'id': genre.id, 'name': genre.name} for genre in preferred_genres],
            'last_updated': timezone.now()
        }
        
        self.set_cached_data(cache_key, response_data)
        return Response(response_data)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create multiple interactions at once
        
        Endpoint: POST /recommendations/v1/interactions/bulk_create/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/interactions/bulk_create/" \
        -d '[{"movie": 123, "interaction_type": "like"}, {"movie": 124, "interaction_type": "dislike"}]'
        """
        if not isinstance(request.data, list):
            return Response(
                {'error': 'Expected a list of interactions'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_interactions = []
        errors = []
        
        for i, interaction_data in enumerate(request.data):
            serializer = UserMovieInteractionCreateSerializer(
                data=interaction_data, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                self.perform_create(serializer)
                created_interactions.append(serializer.data)
            else:
                errors.append({'index': i, 'errors': serializer.errors})
        
        return Response({
            'created': len(created_interactions),
            'errors': errors,
            'interactions': created_interactions
        }, status=status.HTTP_201_CREATED if created_interactions else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_feedback(self, request, pk=None):
        """
        Update feedback for an interaction
        
        Endpoint: PATCH /recommendations/v1/interactions/{id}/update_feedback/
        Example: 
        curl -X PATCH -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/interactions/456/update_feedback/" \
        -d '{"feedback_type": "positive", "feedback_comment": "Great movie!"}'
        """
        interaction = self.get_object()
        
        feedback_type = request.data.get('feedback_type')
        feedback_comment = request.data.get('feedback_comment')
        
        if feedback_type not in ['positive', 'negative', 'neutral']:
            return Response(
                {'error': 'Invalid feedback_type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        interaction.update_feedback(feedback_type, feedback_comment)
        self._clear_user_cache()
        
        serializer = UserMovieInteractionDetailSerializer(
            interaction, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """
        Get interaction analytics for the current user
        
        Endpoint: GET /recommendations/v1/interactions/analytics/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/interactions/analytics/"
        
        Returns time-based analytics (7, 30, 90 days) and genre preferences
        """
        cache_key = self.get_cache_key('user_interaction_analytics', request.user.id)
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        queryset = self.get_queryset()
        
        # Time-based analytics
        now = timezone.now()
        time_ranges = {
            'last_7_days': now - timedelta(days=7),
            'last_30_days': now - timedelta(days=30),
            'last_90_days': now - timedelta(days=90)
        }
        
        analytics_data = {}
        
        for period, start_date in time_ranges.items():
            period_interactions = queryset.filter(timestamp__gte=start_date)
            
            analytics_data[period] = {
                'total_interactions': period_interactions.count(),
                'by_type': dict(period_interactions.values_list('interaction_type').annotate(Count('id'))),
                'average_rating': period_interactions.aggregate(avg=Avg('rating'))['avg'],
                'positive_feedback_rate': period_interactions.filter(
                    is_positive_computed=True
                ).count() / max(period_interactions.count(), 1) * 100
            }
        
        # Genre preferences over time
        genre_analytics = {}
        for genre in UserMovieInteraction.get_user_preferred_genres(request.user):
            genre_interactions = queryset.filter(movie__genres=genre)
            genre_analytics[genre.name] = {
                'total_interactions': genre_interactions.count(),
                'average_rating': genre_interactions.aggregate(avg=Avg('rating'))['avg']
            }
        
        response_data = {
            'time_based': analytics_data,
            'genre_preferences': genre_analytics,
            'generated_at': timezone.now()
        }
        
        self.set_cached_data(cache_key, response_data, timeout=3600)  # Cache for 1 hour
        return Response(response_data)

# USER RECOMMENDATIONS VIEWS
class UserRecommendationViewSet(
    UserContextMixin,
    PerformanceOptimizedMixin,
    CacheableViewMixin,
    viewsets.ReadOnlyModelViewSet
):
    
    model = UserRecommendations
    serializer_class = UserRecommendationListSerializer
    queryset = UserRecommendations.objects.all()
    """
    ViewSet for serving user recommendations.
    
    Read-only viewset that provides personalized movie recommendations.
    Includes A/B testing integration and click tracking.
    
    🎯 PRIMARY ENDPOINT FOR GENRE-BASED PERSONALIZATION:
    GET /recommendations/v1/recommendations/personalized/
    
    Base URL: /recommendations/v1/recommendations/
    """
    queryset = UserRecommendations.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = RecommendationFilter
    ordering_fields = ['score', 'generated_at', 'relevance_score']
    ordering = ['-score', '-generated_at']
    
    # Performance optimization
    select_related_fields = ['user', 'movie']
    prefetch_related_fields = ['movie__genres']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return UserRecommendationListSerializer
        else:
            return UserRecommendationDetailSerializer

    def get_queryset(self):
        """Get fresh recommendations for the current user"""
        queryset = super().get_queryset()
        
        # Only show fresh recommendations (within 7 days)
        fresh_cutoff = timezone.now() - timedelta(days=7)
        queryset = queryset.filter(generated_at__gte=fresh_cutoff)
        
        # Exclude clicked recommendations unless specifically requested
        if not self.request.query_params.get('include_clicked'):
            queryset = queryset.filter(clicked=False)
        
        return queryset

    def list(self, request, *args, **kwargs):
        """
        Get recommendations with A/B testing integration
        
        Endpoint: GET /recommendations/v1/recommendations/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/recommendations/?page=1&page_size=10"
        
        Query Parameters:
        - page: Page number
        - page_size: Items per page  
        - include_clicked: Include already clicked recommendations (default: false)
        - algorithm: Filter by algorithm type
        """
        # Check if user is in an active experiment
        active_experiment = RecommendationExperiment.get_active_experiment()
        algorithm_filter = None
        
        if active_experiment:
            assigned_algorithm = active_experiment.get_algorithm_for_user(request.user)
            algorithm_filter = assigned_algorithm
            
            # Log experiment assignment
            logger.info(f"User {request.user.id} assigned to algorithm {assigned_algorithm} "
                       f"in experiment {active_experiment.name}")
        
        # Apply algorithm filter if in experiment
        queryset = self.filter_queryset(self.get_queryset())
        if algorithm_filter:
            queryset = queryset.filter(algorithm=algorithm_filter)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            
            # Add experiment context to response
            if active_experiment:
                response.data['experiment_context'] = {
                    'experiment_id': active_experiment.id,
                    'experiment_name': active_experiment.name,
                    'assigned_algorithm': algorithm_filter
                }
            
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Get recommendation details
        
        Endpoint: GET /recommendations/v1/recommendations/{id}/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/recommendations/789/"
        """
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def click(self, request, pk=None):
        """
        Mark a recommendation as clicked
        
        Endpoint: POST /recommendations/v1/recommendations/{id}/click/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" \
        "http://localhost:8000/recommendations/v1/recommendations/789/click/"
        """
        recommendation = self.get_object()
        
        if recommendation.clicked:
            return Response(
                {'message': 'Recommendation already marked as clicked'},
                status=status.HTTP_200_OK
            )
        
        recommendation.mark_as_clicked()
        
        # Clear user's recommendation cache
        self._clear_user_cache()
        
        serializer = self.get_serializer(recommendation)
        return Response({
            'message': 'Recommendation marked as clicked',
            'recommendation': serializer.data
        })

    @action(detail=False, methods=['post'])
    def bulk_click(self, request):
        """
        Mark multiple recommendations as clicked
        
        Endpoint: POST /recommendations/v1/recommendations/bulk_click/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/recommendations/bulk_click/" \
        -d '{"recommendation_ids": [789, 790, 791]}'
        """
        recommendation_ids = request.data.get('recommendation_ids', [])
        
        if not recommendation_ids:
            return Response(
                {'error': 'No recommendation IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recommendations = self.get_queryset().filter(id__in=recommendation_ids)
        updated_count = 0
        
        for rec in recommendations:
            if not rec.clicked:
                rec.mark_as_clicked()
                updated_count += 1
        
        self._clear_user_cache()
        
        return Response({
            'message': f'{updated_count} recommendations marked as clicked',
            'updated_count': updated_count
        })

    @action(detail=False, methods=['get'])
    def personalized(self, request):
        """
        🎯 MAIN FUNCTION FOR GENRE-BASED PERSONALIZED RECOMMENDATIONS
        
        Get personalized recommendations based on user's favorite genres (JSON array)
        
        Endpoint: GET /recommendations/v1/recommendations/personalized/
        Example: 
        curl -H "Authorization: Bearer <token>" \
        "http://localhost:8000/recommendations/v1/recommendations/personalized/?limit=20&refresh=true"
        
        Query Parameters:
        - limit: Number of recommendations (default: 20)
        - refresh: Force refresh cache (default: false)
        
        This function uses the user's favorite_genres field (JSON array) to filter recommendations:
        - Extracts genre IDs from user.favorite_genres JSON array
        - Filters movies by matching genres
        - Applies content rating and diversity preferences
        - Returns personalized recommendations with context
        
        Expected favorite_genres format:
        [
            {"genre_id": 28, "weight": 0.8},  # Action
            {"genre_id": 35, "weight": 0.6},  # Comedy  
            {"genre_id": 18, "weight": 0.9}   # Drama
        ]
        or simply: [28, 35, 18]
        """
        user = request.user
        
        cache_key = self.get_cache_key('personalized_recommendations', user.id)
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data and not request.query_params.get('refresh'):
            return Response(cached_data)
        
        queryset = self.get_queryset()
        
        # 🎯 MAIN GENRE FILTERING LOGIC - Uses favorite_genres JSON array
        favorite_genres = getattr(user, 'favorite_genres', [])
        
        if favorite_genres:
            # Extract genre IDs from favorite_genres JSON array
            genre_ids = []
            for genre_item in favorite_genres:
                if isinstance(genre_item, dict):
                    genre_ids.append(genre_item.get('genre_id'))
                elif isinstance(genre_item, int):
                    genre_ids.append(genre_item)
            
            if genre_ids:
                # Filter recommendations by user's favorite genres
                queryset = queryset.filter(movie__genres__in=genre_ids).distinct()
        
        # Apply content rating filter
        content_rating = getattr(user, 'content_rating_preference', None)
        if content_rating:
            queryset = queryset.filter(movie__content_rating=content_rating)
        
        # Apply diversity preference
        diversity_pref = getattr(user, 'diversity_preference', 0.5)
        if diversity_pref > 0.7:
            # High diversity - mix different genres
            queryset = queryset.order_by('movie__genres', '-score')
        else:
            # Low diversity - focus on user's preferred genres
            queryset = queryset.order_by('-score')
        
        # Limit results
        limit = int(request.query_params.get('limit', 20))
        queryset = queryset[:limit]
        
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'recommendations': serializer.data,
            'personalization_context': {
                'has_preferences': bool(favorite_genres),
                'favorite_genre_ids': [item.get('genre_id') if isinstance(item, dict) else item for item in favorite_genres],
                'diversity_level': diversity_pref,
                'total_recommendations': len(serializer.data),
                'content_rating_filter': content_rating
            },
            'generated_at': timezone.now()
        }
        
        self.set_cached_data(cache_key, response_data)
        return Response(response_data)

    def _clear_user_cache(self):
        """Clear cached recommendations for the current user"""
        user_id = self.request.user.id
        cache_keys = [
            f'user_recommendations:{user_id}',
            f'personalized_recommendations:{user_id}'
        ]
        cache.delete_many(cache_keys)

    @action(detail=False, methods=['get'])
    def performance(self, request):
        """
        Get recommendation performance metrics for the current user
        
        Endpoint: GET /recommendations/v1/recommendations/performance/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/recommendations/performance/"
        
        Returns performance metrics by algorithm including click-through rates
        """
        cache_key = self.get_cache_key('user_recommendation_performance', request.user.id)
        cached_data = self.get_cached_data(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        queryset = self.get_queryset()
        
        # Calculate performance metrics by algorithm
        algorithm_performance = {}
        algorithms = queryset.values_list('algorithm', flat=True).distinct()
        
        for algorithm in algorithms:
            algorithm_recs = queryset.filter(algorithm=algorithm)
            total_recs = algorithm_recs.count()
            clicked_recs = algorithm_recs.filter(clicked=True).count()
            
            if total_recs > 0:
                algorithm_performance[algorithm] = {
                    'total_recommendations': total_recs,
                    'clicked_recommendations': clicked_recs,
                    'click_through_rate': (clicked_recs / total_recs) * 100,
                    'average_score': algorithm_recs.aggregate(avg=Avg('score'))['avg']
                }
        
        response_data = {
            'overall_stats': {
                'total_recommendations': queryset.count(),
                'total_clicks': queryset.filter(clicked=True).count(),
                'overall_ctr': (queryset.filter(clicked=True).count() / max(queryset.count(), 1)) * 100
            },
            'by_algorithm': algorithm_performance,
            'generated_at': timezone.now()
        }
        
        self.set_cached_data(cache_key, response_data, timeout=1800)  # Cache for 30 minutes
        return Response(response_data)


# RECOMMENDATION EXPERIMENT VIEWS (ADMIN)

class RecommendationExperimentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing A/B testing experiments.
    
    Admin-only viewset for creating and managing recommendation experiments.
    Provides experiment lifecycle management and statistical analysis.
    
    Base URL: /recommendations/v1/experiments/
    """
    queryset = RecommendationExperiment.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'algorithm_a', 'algorithm_b']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return RecommendationExperimentListSerializer
        else:
            return RecommendationExperimentDetailSerializer

    def list(self, request, *args, **kwargs):
        """
        List all experiments
        
        Endpoint: GET /recommendations/v1/experiments/
        Example: curl -H "Authorization: Bearer <admin_token>" "http://localhost:8000/recommendations/v1/experiments/"
        """
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Create a new experiment
        
        Endpoint: POST /recommendations/v1/experiments/
        Example: 
        curl -X POST -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/experiments/" \
        -d '{"name": "Genre Algorithm Test", "algorithm_a": "collaborative", "algorithm_b": "content_based"}'
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Set creator when creating experiment"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """
        Stop an active experiment
        
        Endpoint: POST /recommendations/v1/experiments/{id}/stop/
        Example: 
        curl -X POST -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/experiments/123/stop/" \
        -d '{"reason": "Significant results achieved"}'
        """
        experiment = self.get_object()
        
        if not experiment.is_active:
            return Response(
                {'error': 'Experiment is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'Manual stop by admin')
        experiment.stop_experiment(reason)
        
        logger.info(f"Experiment {experiment.name} stopped by {request.user.username}: {reason}")
        
        serializer = self.get_serializer(experiment)
        return Response({
            'message': 'Experiment stopped successfully',
            'experiment': serializer.data
        })

    @action(detail=True, methods=['post'])
    def update_results(self, request, pk=None):
        """
        Update experiment statistical results
        
        Endpoint: POST /recommendations/v1/experiments/{id}/update_results/
        Example: 
        curl -X POST -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/experiments/123/update_results/" \
        -d '{"conversion_rate_a": 0.15, "conversion_rate_b": 0.18, "statistical_significance": 0.95}'
        """
        experiment = self.get_object()
        
        serializer = ExperimentResultsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(experiment)
            
            response_serializer = self.get_serializer(experiment)
            return Response({
                'message': 'Results updated successfully',
                'experiment': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """
        Get detailed experiment metrics
        
        Endpoint: GET /recommendations/v1/experiments/{id}/metrics/
        Example: curl -H "Authorization: Bearer <admin_token>" "http://localhost:8000/recommendations/v1/experiments/123/metrics/"
        """
        experiment = self.get_object()
        
        try:
            metrics = experiment.calculate_metrics()
            return Response({
                'experiment_id': experiment.id,
                'experiment_name': experiment.name,
                'metrics': metrics,
                'calculated_at': timezone.now()
            })
        except Exception as e:
            logger.error(f"Error calculating metrics for experiment {experiment.id}: {e}")
            return Response(
                {'error': 'Failed to calculate metrics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get currently active experiment
        
        Endpoint: GET /recommendations/v1/experiments/active/
        Example: curl -H "Authorization: Bearer <admin_token>" "http://localhost:8000/recommendations/v1/experiments/active/"
        """
        active_experiment = RecommendationExperiment.get_active_experiment()
        
        if active_experiment:
            serializer = self.get_serializer(active_experiment)
            return Response(serializer.data)
        
        return Response({'message': 'No active experiment'}, status=status.HTTP_404_NOT_FOUND)

# USER PROFILE VIEWS (Working with User Model)

class UserProfileViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user preferences and onboarding.
    
    Works directly with User model fields - no separate UserProfile model.
    Handles user onboarding, preference management, and cold start data collection.
    
    🎯 MANAGES USER'S FAVORITE_GENRES JSON ARRAY FOR PERSONALIZATION
    
    Base URL: /recommendations/v1/users/
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's profile/preferences
        
        Endpoint: GET /recommendations/v1/users/me/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/users/me/"
        
        Returns user profile including favorite_genres JSON array
        """
        user = request.user
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['patch'])
    def update_preferences(self, request):
        """
        🎯 UPDATE USER'S FAVORITE_GENRES AND OTHER PREFERENCES
        
        Update current user's recommendation preferences including favorite genres
        
        Endpoint: PATCH /recommendations/v1/users/update_preferences/
        Example: 
        curl -X PATCH -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/users/update_preferences/" \
        -d '{"favorite_genres": [{"genre_id": 28, "weight": 0.8}, {"genre_id": 35, "weight": 0.6}], "diversity_preference": 0.7}'
        
        Request body can include:
        - favorite_genres: JSON array of genre preferences
        - content_rating_preference: Preferred content rating
        - diversity_preference: Float between 0-1
        - novelty_preference: Float between 0-1
        """
        user = request.user
        
        serializer = UserProfileSerializer(
            user, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Clear user cache
            self._clear_user_cache()
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def onboarding(self, request):
        """
        🎯 HANDLE USER ONBOARDING - SETS INITIAL FAVORITE_GENRES
        
        Handle user onboarding process including setting favorite genres
        
        Endpoint: POST /recommendations/v1/users/onboarding/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/users/onboarding/" \
        -d '{
            "favorite_genres": [28, 35, 18], 
            "content_rating_preference": "PG-13",
            "country": "US",
            "date_of_birth": "1990-01-01"
        }'
        """
        user = request.user
        
        if getattr(user, 'onboarding_completed', False):
            return Response(
                {'message': 'Onboarding already completed'},
                status=status.HTTP_200_OK
            )
        
        serializer = UserOnboardingSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Clear user cache
            self._clear_user_cache()
            
            # Generate initial recommendations based on preferences
            self._generate_initial_recommendations(user)
            
            logger.info(f"User {request.user.username} completed onboarding")
            
            return Response({
                'message': 'Onboarding completed successfully',
                'profile': UserProfileSerializer(user, context={'request': request}).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def add_genre_preference(self, request):
        """
        🎯 ADD/UPDATE INDIVIDUAL GENRE PREFERENCE IN FAVORITE_GENRES ARRAY
        
        Add or update a single genre preference in the favorite_genres JSON array
        
        Endpoint: POST /recommendations/v1/users/add_genre_preference/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/users/add_genre_preference/" \
        -d '{"genre_id": 28, "weight": 0.9}'
        
        This updates the user's favorite_genres array by adding/updating the specified genre
        """
        user = request.user
        
        serializer = GenrePreferenceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user)
            
            # Clear user cache
            self._clear_user_cache()
            
            return Response({
                'message': 'Genre preference updated',
                'favorite_genres': getattr(user, 'favorite_genres', [])
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def recommendation_context(self, request):
        """
        Get user's recommendation context for ML algorithms
        
        Endpoint: GET /recommendations/v1/users/recommendation_context/
        Example: curl -H "Authorization: Bearer <token>" "http://localhost:8000/recommendations/v1/users/recommendation_context/"
        
        Returns context data used by recommendation algorithms including favorite genres
        """
        user = request.user
        
        # Build context from User model
        age = None
        if getattr(user, 'date_of_birth', None):
            from datetime import date
            today = date.today()
            age = today.year - user.date_of_birth.year
            if today.month < user.date_of_birth.month or (today.month == user.date_of_birth.month and today.day < user.date_of_birth.day):
                age -= 1
        
        # Determine age group
        age_group = None
        if age:
            if age < 18:
                age_group = 'teen'
            elif age < 30:
                age_group = 'young_adult'
            elif age < 50:
                age_group = 'adult'
            else:
                age_group = 'senior'
        
        # Determine cold start strategy
        favorite_genres = getattr(user, 'favorite_genres', [])
        country = getattr(user, 'country', '')
        
        if age and country:
            cold_start_strategy = 'demographic'
        elif favorite_genres:
            cold_start_strategy = 'content_based'
        else:
            cold_start_strategy = 'popular'
        
        context = {
            'user_id': user.id,
            'age': age,
            'age_group': age_group,
            'country': country,
            'favorite_genres': favorite_genres,
            'algorithm_preference': getattr(user, 'algorithm_preference', None),
            'diversity_preference': getattr(user, 'diversity_preference', 0.5),
            'novelty_preference': getattr(user, 'novelty_preference', 0.5),
            'cold_start_strategy': cold_start_strategy,
            'is_new_user': not getattr(user, 'onboarding_completed', False),
            'allow_demographic_targeting': getattr(user, 'allow_demographic_targeting', True)
        }
        
        # Add recent interactions context
        recent_interactions = UserMovieInteraction.objects.filter(
            user=request.user,
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).values('interaction_type').annotate(count=Count('id'))
        
        context['recent_activity'] = {
            item['interaction_type']: item['count'] 
            for item in recent_interactions
        }
        
        serializer = RecommendationContextSerializer(context)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def reset_preferences(self, request):
        """
        Reset user preferences and restart onboarding
        
        Endpoint: POST /recommendations/v1/users/reset_preferences/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" \
        "http://localhost:8000/recommendations/v1/users/reset_preferences/"
        
        Clears all user preferences including favorite_genres and resets onboarding status
        """
        user = request.user
        
        # Reset preference fields on User model
        user.favorite_genres = []
        user.content_rating_preference = None
        user.preferred_decade = None
        user.onboarding_completed = False
        user.cold_start_preferences_collected = False
        user.algorithm_preference = None
        user.diversity_preference = 0.5
        user.novelty_preference = 0.5
        user.save()
        
        # Clear user cache
        self._clear_user_cache()
        
        logger.info(f"User {request.user.username} reset their preferences")
        
        return Response({
            'message': 'Preferences reset successfully',
            'profile': UserProfileSerializer(user, context={'request': request}).data
        })

    def _clear_user_cache(self):
        """Clear all cached data for the current user"""
        user_id = self.request.user.id
        cache_keys = [
            f'user_recommendations:{user_id}',
            f'personalized_recommendations:{user_id}',
            f'user_preferences:{user_id}',
            f'user_interactions_summary:{user_id}',
            f'user_recommendation_performance:{user_id}'
        ]
        cache.delete_many(cache_keys)

    def _generate_initial_recommendations(self, user):
        """Generate initial recommendations for newly onboarded user"""
        try:
            # This would integrate with your recommendation generation pipeline
            logger.info(f"Generating initial recommendations for user {user.username}")
            
            # You would call your recommendation generation service here
            # recommendations_service.generate_for_user(user, strategy='cold_start')
            
        except Exception as e:
            logger.error(f"Failed to generate initial recommendations for user {user.id}: {e}")

# ANALYTICS & REPORTING VIEWs
class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics and reporting endpoints.
    
    Provides dashboard data, performance metrics, and system insights.
    Admin-only access for sensitive analytics data.
    
    Base URL: /recommendations/v1/analytics/
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get dashboard analytics data
        
        Endpoint: GET /recommendations/v1/analytics/dashboard/
        Example: curl -H "Authorization: Bearer <admin_token>" "http://localhost:8000/recommendations/v1/analytics/dashboard/?refresh=true"
        
        Returns comprehensive dashboard metrics for admin overview
        """
        cache_key = 'analytics_dashboard'
        cached_data = cache.get(cache_key)
        
        if cached_data and not request.query_params.get('refresh'):
            return Response(cached_data)
        
        # Calculate time ranges
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # User activity metrics
        user_metrics = {
            'total_users': User.objects.filter(is_active=True).count(),
            'new_users_today': User.objects.filter(date_joined__date=today).count(),
            'new_users_week': User.objects.filter(date_joined__gte=week_ago).count(),
            'onboarded_users': User.objects.filter(onboarding_completed=True).count()
        }
        
        # Interaction metrics
        interaction_metrics = {
            'total_interactions': UserMovieInteraction.objects.count(),
            'interactions_today': UserMovieInteraction.objects.filter(timestamp__date=today).count(),
            'interactions_week': UserMovieInteraction.objects.filter(timestamp__gte=week_ago).count(),
            'positive_interactions': UserMovieInteraction.objects.filter(
                feedback_type='positive'
            ).count()
        }
        
        # Recommendation metrics
        recommendation_metrics = {
            'total_recommendations': UserRecommendations.objects.count(),
            'recommendations_today': UserRecommendations.objects.filter(generated_at__date=today).count(),
            'clicked_recommendations': UserRecommendations.objects.filter(clicked=True).count(),
            'overall_ctr': (UserRecommendations.objects.filter(clicked=True).count() / 
                           max(UserRecommendations.objects.count(), 1)) * 100
        }
        
        # Experiment metrics
        experiment_metrics = {
            'total_experiments': RecommendationExperiment.objects.count(),
            'active_experiments': RecommendationExperiment.objects.filter(is_active=True).count(),
            'completed_experiments': RecommendationExperiment.objects.filter(
                end_date__lt=now
            ).count()
        }
        
        dashboard_data = {
            'user_metrics': user_metrics,
            'interaction_metrics': interaction_metrics,
            'recommendation_metrics': recommendation_metrics,
            'experiment_metrics': experiment_metrics,
            'generated_at': now
        }
        
        cache.set(cache_key, dashboard_data, 300)  # Cache for 5 minutes
        return Response(dashboard_data)

    @action(detail=False, methods=['get'])
    def algorithm_performance(self, request):
        """
        Get performance comparison of different algorithms
        
        Endpoint: GET /recommendations/v1/analytics/algorithm_performance/
        Example: curl -H "Authorization: Bearer <admin_token>" "http://localhost:8000/recommendations/v1/analytics/algorithm_performance/"
        """
        algorithms = UserRecommendations.objects.values_list('algorithm', flat=True).distinct()
        
        performance_data = []
        for algorithm in algorithms:
            performance = UserRecommendations.get_algorithm_performance(algorithm)
            performance_data.append(performance)
        
        return Response({
            'algorithm_performance': performance_data,
            'generated_at': timezone.now()
        })

    @action(detail=False, methods=['get'])
    def user_segmentation(self, request):
        """
        Get user segmentation analytics
        
        Endpoint: GET /recommendations/v1/analytics/user_segmentation/
        Example: curl -H "Authorization: Bearer <admin_token>" "http://localhost:8000/recommendations/v1/analytics/user_segmentation/"
        """
        # Age group distribution (from User.date_of_birth)
        users_with_age = User.objects.exclude(date_of_birth__isnull=True)
        age_groups = {'teen': 0, 'young_adult': 0, 'adult': 0, 'senior': 0}
        
        for user in users_with_age:
            age = self._calculate_age(user.date_of_birth)
            if age:
                if age < 18:
                    age_groups['teen'] += 1
                elif age < 30:
                    age_groups['young_adult'] += 1
                elif age < 50:
                    age_groups['adult'] += 1
                else:
                    age_groups['senior'] += 1
        
        # Country distribution
        country_dist = User.objects.exclude(
            country__isnull=True
        ).exclude(country='').values('country').annotate(count=Count('id')).order_by('-count')[:10]
        
        # Onboarding status
        onboarding_stats = {
            'total_users': User.objects.count(),
            'onboarded': User.objects.filter(onboarding_completed=True).count(),
            'has_preferences': User.objects.exclude(favorite_genres=[]).count()
        }
        
        return Response({
            'age_groups': [{'age_group': k, 'count': v} for k, v in age_groups.items()],
            'top_countries': list(country_dist),
            'onboarding_stats': onboarding_stats,
            'generated_at': timezone.now()
        })

    def _calculate_age(self, birth_date):
        """Calculate age from birth date"""
        if not birth_date:
            return None
        from datetime import date
        today = date.today()
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age

# UTILITY VIEWS

class RecommendationUtilityViewSet(viewsets.ViewSet):
    """
    Utility endpoints for recommendation system management.
    
    Provides maintenance, health checks, and administrative utilities.
    
    Base URL: /recommendations/v1/utils/
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def generate_recommendations(self, request):
        """
        Trigger recommendation generation for current user
        
        Endpoint: POST /recommendations/v1/utils/generate_recommendations/
        Example: 
        curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
        "http://localhost:8000/recommendations/v1/utils/generate_recommendations/" \
        -d '{"algorithm": "collaborative_filtering", "limit": 20}'
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        algorithm = request.data.get('algorithm', 'collaborative_filtering')
        limit = int(request.data.get('limit', 10))
        
        try:
            # This would integrate with your ML pipeline
            recommendations = UserRecommendations.generate_for_user(
                user=request.user,
                algorithm=algorithm,
                limit=limit
            )
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {request.user.username}")
            
            return Response({
                'message': f'Generated {len(recommendations)} recommendations',
                'algorithm': algorithm,
                'count': len(recommendations)
            })
        
        except Exception as e:
            logger.error(f"Failed to generate recommendations for user {request.user.id}: {e}")
            return Response(
                {'error': 'Failed to generate recommendations'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def health(self, request):
        """
        Health check endpoint
        
        Endpoint: GET /recommendations/v1/utils/health/
        Example: curl "http://localhost:8000/recommendations/v1/utils/health/"
        """
        try:
            # Test database connectivity
            user_count = User.objects.count()
            
            # Test cache connectivity
            cache_key = 'health_check'
            cache.set(cache_key, 'ok', 60)
            cache_status = cache.get(cache_key) == 'ok'
            
            return Response({
                'status': 'healthy',
                'database': 'connected',
                'cache': 'connected' if cache_status else 'disconnected',
                'user_count': user_count,
                'timestamp': timezone.now()
            })
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now()
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)