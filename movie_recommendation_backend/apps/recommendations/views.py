# recommendations/views.py
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import UserMovieInteraction, UserRecommendations
from .serializers import (
    UserMovieInteractionSerializer,
    UserMovieInteractionCreateSerializer,
    UserRecommendationSerializer,
    UserRecommendationCreateSerializer,
    UserPreferencesSerializer,
    RecommendationPerformanceSerializer,
    InteractionWithMovieSerializer,
    RecommendationWithMovieSerializer,
)

User = get_user_model()


# === USER INTERACTION VIEWS ===

class UserInteractionListCreateView(generics.ListCreateAPIView):
    """
    List all interactions or create a new interaction.
    GET: Returns paginated list of user interactions
    POST: Creates new interaction (like, rating, etc.)
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter interactions by current user"""
        return UserMovieInteraction.objects.filter(
            user=self.request.user
        ).select_related('movie', 'user')
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.request.method == 'POST':
            return UserMovieInteractionCreateSerializer
        return UserMovieInteractionSerializer
    
    def perform_create(self, serializer):
        """Set user automatically when creating interaction"""
        serializer.save(user=self.request.user)


class UserInteractionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific interaction.
    GET: Get interaction details
    PUT/PATCH: Update interaction (like change rating)
    DELETE: Remove interaction
    """
    
    serializer_class = UserMovieInteractionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """User can only access their own interactions"""
        return UserMovieInteraction.objects.filter(user=self.request.user)


class MovieInteractionsView(generics.ListAPIView):
    """
    Get all interactions for a specific movie.
    Useful for seeing how popular a movie is.
    """
    
    serializer_class = UserMovieInteractionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        movie_id = self.kwargs['movie_id']
        return UserMovieInteraction.objects.filter(
            movie_id=movie_id
        ).select_related('user', 'movie')


# === RECOMMENDATION VIEWS ===

class UserRecommendationCreateView(generics.CreateAPIView):
    """
    Create individual recommendations manually.
    Used by algorithms or admins to create specific recommendations.
    POST: Create a new recommendation for a user-movie-algorithm combination
    """
    
    serializer_class = UserRecommendationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        """Add any additional logic when creating recommendation"""
        recommendation = serializer.save()
        
        # Optional: Log that a recommendation was manually created
        UserMovieInteraction.create_interaction(
            user=recommendation.user,
            movie=recommendation.movie,
            interaction_type='recommendation_created',
            source='api',
            metadata={
                'recommendation_id': recommendation.id,
                'algorithm': recommendation.algorithm,
                'score': float(recommendation.score),
                'created_via': 'manual_api'
            }
        )
        
        return recommendation
    
    def create(self, request, *args, **kwargs):
        """Override to provide detailed response"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        recommendation = self.perform_create(serializer)
        
        # Return recommendation with full details
        response_serializer = UserRecommendationSerializer(recommendation)
        
        return Response({
            'message': 'Recommendation created successfully',
            'recommendation': response_serializer.data,
            'created_at': recommendation.generated_at
        }, status=status.HTTP_201_CREATED)


class UserRecommendationsView(generics.ListAPIView):
    """
    Get personalized recommendations for current user.
    Supports filtering by algorithm and freshness.
    """
    
    serializer_class = RecommendationWithMovieSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get fresh recommendations for current user"""
        queryset = UserRecommendations.objects.filter(
            user=self.request.user
        ).select_related('movie')
        
        # Filter by algorithm if specified
        algorithm = self.request.query_params.get('algorithm')
        if algorithm:
            queryset = queryset.filter(algorithm=algorithm)
        
        # Filter by freshness
        fresh_only = self.request.query_params.get('fresh_only', 'true')
        if fresh_only.lower() == 'true':
            cutoff = timezone.now() - timedelta(days=7)
            queryset = queryset.filter(generated_at__gte=cutoff)
        
        return queryset.order_by('-relevance_score', '-generated_at')
    
    def list(self, request, *args, **kwargs):
        """Override to add extra context"""
        queryset = self.get_queryset()
        
        # If no recommendations exist, generate them
        if not queryset.exists():
            try:
                UserRecommendations.generate_for_user(request.user)
                queryset = self.get_queryset()  # Refresh queryset
            except Exception as e:
                return Response({
                    'error': 'Failed to generate recommendations',
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Standard list response with pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RecommendationClickView(APIView):
    """
    Track when user clicks on a recommendation.
    POST: Mark recommendation as clicked and log interaction.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, recommendation_id):
        """Mark recommendation as clicked"""
        try:
            recommendation = get_object_or_404(
                UserRecommendations,
                id=recommendation_id,
                user=request.user
            )
            
            # Mark as clicked (this also logs the interaction)
            recommendation.mark_as_clicked()
            
            # Return updated recommendation data
            serializer = UserRecommendationSerializer(recommendation)
            
            return Response({
                'message': 'Recommendation marked as clicked',
                'recommendation': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to mark recommendation as clicked',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# === ANALYTICS AND PREFERENCES VIEWS ===

class UserPreferencesView(APIView):
    """
    Get user's preferences and behavior analytics.
    Shows what genres they like, rating patterns, etc.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return user's preference analysis"""
        user = request.user
        serializer = UserPreferencesSerializer(user)
        
        return Response({
            'preferences': serializer.data,
            'metadata': {
                'analysis_date': timezone.now(),
                'total_users': User.objects.count(),
                'user_rank': self.get_user_engagement_rank(user)
            }
        })
    
    def get_user_engagement_rank(self, user):
        """Calculate user's engagement rank among all users"""
        user_interaction_count = UserMovieInteraction.objects.filter(user=user).count()
        
        higher_engagement_users = User.objects.annotate(
            interaction_count=Count('movie_interactions')
        ).filter(interaction_count__gt=user_interaction_count).count()
        
        total_users = User.objects.count()
        percentile = ((total_users - higher_engagement_users) / total_users) * 100
        
        return {
            'percentile': round(percentile, 1),
            'total_interactions': user_interaction_count
        }


class TrendingMoviesView(generics.ListAPIView):
    """
    Get trending movies based on recent user interactions.
    Shows what's popular right now.
    """
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get(self, request):
        """Return trending movies with analytics"""
        days = int(request.query_params.get('days', 7))
        limit = int(request.query_params.get('limit', 20))
        
        # Get trending data
        trending_data = UserMovieInteraction.get_trending_movies(
            days=days,
            interaction_types=['view', 'like', 'favorite', 'rating']
        )[:limit]
        
        # Enhance with additional movie data
        enhanced_trending = []
        for movie_data in trending_data:
            try:
                from movies.models import Movie  # Adjust import as needed
                movie = Movie.objects.get(id=movie_data['movie'])
                
                enhanced_trending.append({
                    'movie_id': movie.id,
                    'movie_title': movie.title,
                    'interaction_count': movie_data['interaction_count'],
                    'unique_users': movie_data['unique_users'],
                    'average_rating': UserMovieInteraction.get_movie_average_rating(movie),
                    'poster_url': getattr(movie, 'poster_url', None),
                })
            except:
                continue
        
        return Response({
            'trending_movies': enhanced_trending,
            'period_days': days,
            'last_updated': timezone.now()
        })


class AlgorithmPerformanceView(APIView):
    """
    Analytics view for recommendation algorithm performance.
    Used by admins and data scientists to monitor algorithm effectiveness.
    """
    
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        """Return performance analytics for all algorithms"""
        days = int(request.query_params.get('days', 30))
        
        # Get all algorithms
        algorithms = UserRecommendations.objects.values_list(
            'algorithm', flat=True
        ).distinct()
        
        performance_data = []
        for algorithm in algorithms:
            performance = UserRecommendations.get_algorithm_performance(algorithm, days)
            performance_data.append(performance)
        
        # Sort by click-through rate
        performance_data.sort(key=lambda x: x['click_through_rate'], reverse=True)
        
        serializer = RecommendationPerformanceSerializer(performance_data, many=True)
        
        return Response({
            'algorithm_performance': serializer.data,
            'analysis_period': f'{days} days',
            'total_algorithms': len(algorithms),
            'best_algorithm': performance_data[0]['algorithm'] if performance_data else None
        })


# === RECOMMENDATION GENERATION VIEWS ===

class GenerateRecommendationsView(APIView):
    """
    Manually trigger recommendation generation.
    Useful for testing and on-demand generation.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Generate recommendations for current user"""
        algorithm = request.data.get('algorithm', 'collaborative_filtering')
        limit = int(request.data.get('limit', 10))
        force_regenerate = request.data.get('force_regenerate', False)
        
        try:
            # Check if user already has fresh recommendations
            if not force_regenerate:
                existing_recs = UserRecommendations.get_user_recommendations(
                    request.user, limit=limit, algorithm=algorithm
                )
                if existing_recs:
                    serializer = UserRecommendationSerializer(existing_recs, many=True)
                    return Response({
                        'message': 'Using existing recommendations',
                        'recommendations': serializer.data,
                        'generated_new': False
                    })
            
            # Generate new recommendations
            recommendations = UserRecommendations.generate_for_user(
                request.user, algorithm=algorithm, limit=limit
            )
            
            serializer = UserRecommendationSerializer(recommendations, many=True)
            
            return Response({
                'message': f'Generated {len(recommendations)} recommendations',
                'recommendations': serializer.data,
                'algorithm': algorithm,
                'generated_new': True
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': 'Failed to generate recommendations',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class SimilarUsersView(APIView):
    """
    Find users with similar movie preferences.
    Useful for user discovery and social features.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get users similar to current user"""
        min_common = int(request.query_params.get('min_common_movies', 3))
        limit = int(request.query_params.get('limit', 10))
        
        try:
            similar_user_ids = UserMovieInteraction.get_similar_users(
                request.user, min_common_movies=min_common
            )[:limit]
            
            # Get user details
            similar_users = User.objects.filter(id__in=similar_user_ids)
            
            user_data = []
            for user in similar_users:
                # Get common movies
                user_movies = set(UserMovieInteraction.objects.filter(
                    user=user
                ).values_list('movie_id', flat=True))
                
                current_user_movies = set(UserMovieInteraction.objects.filter(
                    user=request.user
                ).values_list('movie_id', flat=True))
                
                common_movies = len(user_movies & current_user_movies)
                
                user_data.append({
                    'user_id': user.id,
                    'username': user.username,
                    'common_movies_count': common_movies,
                    'total_interactions': UserMovieInteraction.objects.filter(user=user).count()
                })
            
            return Response({
                'similar_users': user_data,
                'criteria': {
                    'min_common_movies': min_common,
                    'limit': limit
                }
            })
            
        except Exception as e:
            return Response({
                'error': 'Failed to find similar users',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# === MOVIE-SPECIFIC VIEWS ===

class MovieRecommendationsView(APIView):
    """
    Get users who might be interested in a specific movie.
    Useful for targeted marketing and notifications.
    """
    
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, movie_id):
        """Find users who might like this movie"""
        try:
            from movies.models import Movie  # Adjust import
            movie = get_object_or_404(Movie, id=movie_id)
            
            # Find users who like movies in same genres
            movie_genres = movie.genres.all() if hasattr(movie, 'genres') else []
            
            if not movie_genres:
                return Response({
                    'message': 'Movie has no genres for recommendation targeting',
                    'target_users': []
                })
            
            # Find users who interacted positively with movies in same genres
            target_users = User.objects.filter(
                movie_interactions__movie__genres__in=movie_genres,
                movie_interactions__interaction_type__in=['like', 'favorite', 'rating'],
                movie_interactions__rating__gte=4.0
            ).exclude(
                movie_interactions__movie=movie  # Exclude users who already interacted
            ).annotate(
                genre_matches=Count('movie_interactions__movie__genres', distinct=True)
            ).filter(
                genre_matches__gte=2  # At least 2 genre matches
            ).distinct()[:50]
            
            user_data = []
            for user in target_users:
                user_data.append({
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'genre_affinity': UserMovieInteraction.get_user_preferred_genres(user)[:3]
                })
            
            return Response({
                'movie': {
                    'id': movie.id,
                    'title': movie.title,
                    'genres': [genre.name for genre in movie_genres]
                },
                'target_users': user_data,
                'targeting_criteria': 'Users with 2+ matching genre preferences'
            })
            
        except Exception as e:
            return Response({
                'error': 'Failed to find target users',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# === ANALYTICS VIEWS ===

class UserActivityFeedView(generics.ListAPIView):
    """
    Get user's recent activity feed with movie details.
    Perfect for "Your Activity" or "Recently Watched" sections.
    """
    
    serializer_class = InteractionWithMovieSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get recent activity for current user"""
        days = int(self.request.query_params.get('days', 30))
        cutoff = timezone.now() - timedelta(days=days)
        
        return UserMovieInteraction.objects.filter(
            user=self.request.user,
            timestamp__gte=cutoff
        ).select_related('movie').order_by('-timestamp')


class RecommendationFeedView(generics.ListAPIView):
    """
    Get user's recommendation feed with full movie details.
    Perfect for homepage recommendation carousels.
    """
    
    serializer_class = RecommendationWithMovieSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get top recommendations with full movie data"""
        return UserRecommendations.get_user_recommendations(
            self.request.user,
            limit=20
        ).select_related('movie')


# === ADMIN/STAFF VIEWS ===

class GenerateBatchRecommendationsView(APIView):
    """
    Generate recommendations for all users (admin only).
    Used for batch processing and system maintenance.
    """
    
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        """Trigger batch recommendation generation"""
        algorithm = request.data.get('algorithm', 'collaborative_filtering')
        batch_size = int(request.data.get('batch_size', 100))
        
        try:
            total_generated = UserRecommendations.generate_for_all_users(
                algorithm=algorithm,
                batch_size=batch_size
            )
            
            return Response({
                'message': 'Batch generation completed',
                'total_recommendations_generated': total_generated,
                'algorithm': algorithm
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': 'Batch generation failed',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class SendRecommendationNotificationsView(APIView):
    """
    Send recommendation notifications to users (admin only).
    Triggers your notification system.
    """
    
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        """Send notifications for fresh recommendations"""
        algorithm = request.data.get('algorithm')
        limit_per_user = int(request.data.get('limit_per_user', 5))
        
        try:
            notifications_sent = UserRecommendations.send_batch_notifications(
                algorithm=algorithm,
                limit_per_user=limit_per_user
            )
            
            return Response({
                'message': 'Notifications sent successfully',
                'notifications_sent': notifications_sent,
                'algorithm_filter': algorithm or 'all'
            })
            
        except Exception as e:
            return Response({
                'error': 'Failed to send notifications',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class SystemCleanupView(APIView):
    """
    Clean up old recommendations and optimize database.
    Admin maintenance endpoint.
    """
    
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        """Perform system cleanup"""
        days = int(request.data.get('days', 30))
        
        try:
            # Clean old recommendations
            deleted_recs = UserRecommendations.cleanup_old_recommendations(days=days)
            
            # Could add more cleanup operations here:
            # - Clean old interactions
            # - Update popularity metrics
            # - Refresh user preferences cache
            
            return Response({
                'message': 'System cleanup completed',
                'deleted_recommendations': deleted_recs,
                'cleanup_criteria': f'Older than {days} days and unclicked'
            })
            
        except Exception as e:
            return Response({
                'error': 'Cleanup failed',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# === FUNCTION-BASED VIEWS ===

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def quick_interaction(request):
    """
    Quick endpoint for simple interactions (like, dislike, etc.).
    Optimized for mobile apps and quick actions.
    """
    
    movie_id = request.data.get('movie_id')
    interaction_type = request.data.get('interaction_type')
    rating = request.data.get('rating')
    
    if not movie_id or not interaction_type:
        return Response({
            'error': 'movie_id and interaction_type are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create interaction using model method
        interaction = UserMovieInteraction.create_interaction(
            user=request.user,
            movie_id=movie_id,
            interaction_type=interaction_type,
            rating=rating,
            source=request.data.get('source', 'web')
        )
        
        serializer = UserMovieInteractionSerializer(interaction)
        
        return Response({
            'message': 'Interaction recorded',
            'interaction': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': 'Failed to record interaction',
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recommendation_stats(request):
    """
    Get user's personal recommendation statistics.
    Shows how well the system is working for them.
    """
    
    user = request.user
    
    # Calculate user's recommendation stats
    total_recs = UserRecommendations.objects.filter(user=user).count()
    clicked_recs = UserRecommendations.objects.filter(user=user, clicked=True).count()
    
    recent_recs = UserRecommendations.objects.filter(
        user=user,
        generated_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Algorithm breakdown
    algorithm_stats = UserRecommendations.objects.filter(user=user).values(
        'algorithm'
    ).annotate(
        count=Count('id'),
        clicked_count=Count('id', filter=Q(clicked=True)),
        avg_score=Avg('score')
    )
    
    return Response({
        'user_stats': {
            'total_recommendations': total_recs,
            'clicked_recommendations': clicked_recs,
            'click_through_rate': round(clicked_recs / total_recs * 100, 2) if total_recs > 0 else 0,
            'recent_recommendations': recent_recs,
        },
        'algorithm_breakdown': list(algorithm_stats),
        'personalization_level': 'High' if total_recs > 50 else 'Medium' if total_recs > 10 else 'Low'
    })


# === SEARCH AND DISCOVERY VIEWS ===

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def discover_movies(request):
    """
    Discover new movies based on user preferences.
    Different from recommendations - focuses on exploration.
    """
    
    user = request.user
    
    # Get user's least explored genres
    user_preferred = UserMovieInteraction.get_user_preferred_genres(user)
    
    # Find highly-rated movies in adjacent genres
    from movies.models import Movie
    
    discovery_movies = Movie.objects.exclude(
        interactions__user=user  # Movies user hasn't interacted with
    ).filter(
        genres__in=user_preferred  # But in genres they like
    ).annotate(
        avg_rating=Avg('interactions__rating'),
        interaction_count=Count('interactions')
    ).filter(
        avg_rating__gte=4.0,  # Highly rated
        interaction_count__gte=10  # Popular enough
    ).order_by('-avg_rating')[:15]
    
    movie_data = []
    for movie in discovery_movies:
        movie_data.append({
            'id': movie.id,
            'title': movie.title,
            'average_rating': float(movie.avg_rating) if movie.avg_rating else None,
            'interaction_count': movie.interaction_count,
            'genres': [genre.name for genre in movie.genres.all()] if hasattr(movie, 'genres') else [],
            'discovery_reason': 'Highly rated in your preferred genres'
        })
    
    return Response({
        'discovery_movies': movie_data,
        'discovery_criteria': {
            'min_rating': 4.0,
            'min_interactions': 10,
            'based_on_genres': [genre.name for genre in user_preferred]
        }
    })