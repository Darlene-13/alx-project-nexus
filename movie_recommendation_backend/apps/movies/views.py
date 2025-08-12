"""
This is our movie recommendation views file for the movies app.
It contains views for our movie models.
Includes different views for listing, creating, updating, and deleting movies.
"""
import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination


from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F, Count, Avg, Sum
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db import models
from django.contrib.auth import get_user_model

from .models import Movie, Genre, MovieGenre
from .serializers import (
    MovieListSerializer, MovieDetailSerializer, MovieCreateUpdateSerializer,
    MovieStatsSerializer, MovieRecommendationSerializer,
    GenreSerializer, GenreDetailSerializer, MovieSearchSerializer
)

from .filters import MovieFilter

from django.shortcuts import render

# Initialize logger
logger = logging.getLogger(__name__)

def movie_hub(request):
    """Movies app hub showing all available endpoints, grouped by section."""

    endpoints_by_section = {
        "🎬 MOVIES": [
            {"method": "GET",    "url": "/movies/api/movies/",                  "description": "List all movies",       "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/movies/{pk}/",            "description": "Retrieve movie details", "status": "✅ Active"},
            {"method": "PUT",    "url": "/movies/api/movies/{pk}/",            "description": "Update movie",           "status": "✅ Active"},
            {"method": "PATCH",  "url": "/movies/api/movies/{pk}/",            "description": "Partial update",         "status": "✅ Active"},
            {"method": "DELETE", "url": "/movies/api/movies/{pk}/",            "description": "Delete movie",           "status": "✅ Active"},
        ],
        "🎯 MOVIE CUSTOM ACTIONS": [
            {"method": "GET",    "url": "/movies/api/movies/popular/",                     "description": "Popular movies",       "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/movies/top_rated/",                   "description": "Top-rated movies",     "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/movies/recent/",                      "description": "Recently released",    "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/movies/by_genre/",       "description": "Movies by genre",      "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/movies/stats/",                       "description": "Movie stats",          "status": "✅ Active"},
            {"method": "POST",   "url": "/movies/api/movies/{pk}/increment_views/",        "description": "Increment views",      "status": "✅ Active"},
            {"method": "POST",   "url": "/movies/api/movies/{pk}/increment_likes/",        "description": "Increment likes",      "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/movies/{pk}/similar/",                "description": "Similar movies",       "status": "✅ Active"},
        ],
        "📚 GENRES": [
            {"method": "GET",    "url": "/movies/api/genres/",                  "description": "List genres",             "status": "✅ Active"},
            {"method": "POST",   "url": "/movies/api/genres/",                  "description": "Create genre",            "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/genres/{pk}/",            "description": "Genre details",           "status": "✅ Active"},
            {"method": "PUT",    "url": "/movies/api/genres/{pk}/",            "description": "Update genre",            "status": "✅ Active"},
            {"method": "PATCH",  "url": "/movies/api/genres/{pk}/",            "description": "Partial update",          "status": "✅ Active"},
            {"method": "DELETE", "url": "/movies/api/genres/{pk}/",            "description": "Delete genre",            "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/genres/{pk}/movies/",     "description": "Movies in genre",         "status": "✅ Active"},
        ],
        "🔎 SEARCH & RECOMMENDATIONS": [
            {"method": "GET", "url": "/movies/api/search/?q=batman",             "description": "Advanced search",         "status": "✅ Active"},
            {"method": "GET", "url": "/movies/api/recommendations/?type=popular","description": "Recommendations",         "status": "✅ Active"},
        ],
        "📊 ANALYTICS": [
            {"method": "GET", "url": "/movies/api/analytics/",                  "description": "Analytics overview",      "status": "✅ Active"},
        ],
        "📘 API DOCUMENTATION": [
            {"method": "GET", "url": "/movies/docs/",   "description": "Swagger UI",   "status": "✅ Active"},
            {"method": "GET", "url": "/movies/redoc/",  "description": "ReDoc UI",      "status": "✅ Active"},
            {"method": "GET", "url": "/movies/schema/", "description": "Schema (JSON)", "status": "✅ Active"},
        ],
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
    
    return render(request, 'movies/movie_hub.html', context)

from rest_framework.pagination import PageNumberPagination

class StandardResultsPagination(PageNumberPagination):

    """
    Standard pagination class for our API.
    This class provides pagination for our API responses.
    It uses page number based pagination.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class MovieViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on the Movie model.
    
    Endpoints:
    - GET    /api/movies/           # List all movies
    - POST   /api/movies/           # Create new movie
    - GET    /api/movies/{id}/      # Get movie details  
    - PUT    /api/movies/{id}/      # Update movie
    - PATCH  /api/movies/{id}/      # Partial update
    - DELETE /api/movies/{id}/      # Delete movie
    """
    queryset = Movie.objects.select_related().prefetch_related('genres')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MovieFilter
    ordering_fields = ['release_date', 'popularity_score', 'tmdb_rating', 'views', 'like_count']
    ordering = ['-release_date']

    def get_serializer_class(self):
        """Returns appropriate serializer based on action."""
        if self.action == 'list':
            return MovieListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return MovieCreateUpdateSerializer
        elif self.action == 'stats':
            return MovieStatsSerializer
        return MovieDetailSerializer

    def get_queryset(self):
        """Optimize queryset based on action."""
        queryset = Movie.objects.select_related().prefetch_related('genres')
        
        if self.action == 'list':
            queryset = queryset.defer('overview', 'tagline')  # Optimize list view
        
        return queryset

    def list(self, request, *args, **kwargs):
        """
        GET /api/movies/
        List all movies with filtering and pagination.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        POST /api/movies/
        Create a new movie.
        
        Body: {
            "title": "New Movie",
            "overview": "Movie description",
            "release_date": "2024-01-01",
            "tmdb_rating": 8.5,
            "genres": [1, 2, 3]
        }
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            movie = serializer.save()
            return Response(
                MovieDetailSerializer(movie).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ... keep all your existing custom actions (@action methods) here ...
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """GET /api/movies/popular/ - Popular movies by popularity score"""
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = min(limit, 100)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid limit parameter'}, status=400)
        
        movies = self.get_queryset().order_by('-popularity_score')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """GET /api/movies/top_rated/ - Top-rated movies"""
        try:
            min_rating = float(request.query_params.get('min_rating', 7.0))
            limit = int(request.query_params.get('limit', 10))
            limit = min(limit, 100)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid parameters'}, status=400)
            
        movies = self.get_queryset().filter(tmdb_rating__gte=min_rating).order_by('-tmdb_rating')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """GET /api/movies/recent/ - Recently released movies"""
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = min(limit, 100)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid limit parameter'}, status=400)
        
        movies = self.get_queryset().order_by('-release_date')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_genre(self, request):
        """GET /api/movies/by_genre/?genre=Action - Movies by genre name"""
        genre_name = request.query_params.get('genre')
        if not genre_name:
            return Response({'error': 'Genre name is required'}, status=400)
        
        try:
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid limit parameter'}, status=400)

        movies = self.get_queryset().filter(genres__name__iexact=genre_name).order_by('-release_date')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """GET /api/movies/stats/ - Platform statistics"""
        from datetime import datetime, timedelta
        from django.contrib.auth import get_user_model
        
        month_ago = datetime.now() - timedelta(days=30)
        
        stats = {
            'total_movies': Movie.objects.count(),
            'total_views': Movie.objects.aggregate(total=Sum('views'))['total'] or 0,
            'total_likes': Movie.objects.aggregate(total=Sum('like_count'))['total'] or 0,
            'avg_rating': round(Movie.objects.aggregate(avg=Avg('tmdb_rating'))['avg'] or 0, 1),
            'recent_additions': Movie.objects.filter(created_at__gte=month_ago).count(),
        }
        
        try:
            User = get_user_model()
            stats['total_users'] = User.objects.count()
        except:
            pass
        
        return Response(stats)

    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """POST /api/movies/{id}/increment_views/ - Increment view count"""
        movie = self.get_object()
        Movie.objects.filter(id=movie.id).update(views=F('views') + 1)
        movie.refresh_from_db()
        return Response({'views': movie.views})

    @action(detail=True, methods=['post'])
    def increment_likes(self, request, pk=None):
        """POST /api/movies/{id}/increment_likes/ - Increment like count"""
        movie = self.get_object()
        Movie.objects.filter(id=movie.id).update(like_count=F('like_count') + 1)
        movie.refresh_from_db()
        return Response({'likes': movie.like_count})

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """GET /api/movies/{id}/similar/ - Get similar movies"""
        try:
            movie = self.get_object()
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid limit parameter'}, status=400)

        similar_movies = (
            Movie.objects.filter(genres__in=movie.genres.all()).exclude(id=movie.id)
            .annotate(genre_matches=Count('genres'))
            .order_by('-genre_matches', '-tmdb_rating')
            .distinct()[:limit]
        )
        serializer = MovieListSerializer(similar_movies, many=True)
        return Response(serializer.data)

class GenreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on the Genre model.
    
    Endpoints:
    - GET    /api/genres/           # List all genres
    - POST   /api/genres/           # Create new genre  
    - GET    /api/genres/{id}/      # Get genre details
    - PUT    /api/genres/{id}/      # Update genre
    - PATCH  /api/genres/{id}/      # Partial update
    - DELETE /api/genres/{id}/      # Delete genre
    """
    queryset = Genre.objects.annotate(movie_count=Count('movies')).order_by('name')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'movie_count']
    ordering = ['name']

    def get_serializer_class(self):
        """Returns appropriate serializer based on action."""
        if self.action == 'list':
            return GenreDetailSerializer  # Shows movie count
        elif self.action in ['create', 'update', 'partial_update']:
            return GenreSerializer  # For input validation
        return GenreDetailSerializer

    def list(self, request, *args, **kwargs):
        """
        GET /api/genres/
        List all genres with movie counts.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Add search functionality
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        POST /api/genres/
        Create a new genre.
        
        Body: {
            "name": "Sci-Fi",
            "description": "Science Fiction movies"
        }
        """
        # Check for duplicate names (case-insensitive)
        name = request.data.get('name', '').strip()
        if not name:
            return Response(
                {'error': 'Genre name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Genre.objects.filter(name__iexact=name).exists():
            return Response(
                {'error': f'Genre "{name}" already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            genre = serializer.save()
            return Response(
                GenreDetailSerializer(genre).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/genres/{id}/
        Delete a genre with safety checks.
        """
        genre = self.get_object()
        movie_count = genre.movies.count()
        
        # Safety check - prevent deletion if genre has movies
        if movie_count > 0:
            force = request.query_params.get('force', '').lower() == 'true'
            if not force:
                return Response(
                    {
                        'error': f'Cannot delete genre "{genre.name}" because it has {movie_count} movies',
                        'suggestion': 'Add ?force=true to force delete (this will remove genre from all movies)'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """
        GET /api/genres/popular/
        Get most popular genres by movie count.
        """
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = min(limit, 50)  # Cap at 50
        except (ValueError, TypeError):
            limit = 10

        popular_genres = self.get_queryset().order_by('-movie_count')[:limit]
        serializer = self.get_serializer(popular_genres, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        GET /api/genres/stats/
        Get genre statistics and insights.
        """
        from django.db.models import Avg, Max, Min

        # Basic stats
        genre_stats = Genre.objects.aggregate(
            total_genres=Count('id'),
            genres_with_movies=Count('id', filter=Q(movies__isnull=False)),
        )

        # Top genres by movie count
        top_genres = Genre.objects.annotate(
            movie_count=Count('movies')
        ).order_by('-movie_count')[:5].values('name', 'movie_count')

        # Empty genres (content gaps)
        empty_genres = Genre.objects.annotate(
            movie_count=Count('movies')
        ).filter(movie_count=0).values_list('name', flat=True)

        return Response({
            'overview': genre_stats,
            'top_genres': list(top_genres),
            'empty_genres': list(empty_genres),
            'empty_genres_count': len(empty_genres)
        })
    
    @action(detail=True, methods=['get'], url_path='movies')

    def movies(self, request, pk=None):
        """
        Get all movies for a specific genre.
        
        GET /movies/api/genres/{pk}/movies/
        
        Returns paginated list of movies that belong to this genre.
        """
        try:
            genre = self.get_object()  # Gets the genre by pk
            
            # Get movies that have this genre
            movies = Movie.objects.filter(
                genres=genre,
                is_active=True  # Only show active movies
            ).select_related(
                'director'
            ).prefetch_related(
                'genres', 'cast'
            ).order_by('-release_date')
            
            # Apply pagination
            page = self.paginate_queryset(movies)
            if page is not None:
                serializer = MovieListSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            # If no pagination
            serializer = MovieListSerializer(movies, many=True, context={'request': request})
            
            return Response({
                'genre': {
                    'id': genre.id,
                    'name': genre.name
                },
                'movies': serializer.data,
                'total_movies': movies.count(),
                'message': f'Movies in {genre.name} genre retrieved successfully'
            }, status=status.HTTP_200_OK)
            
        except Genre.DoesNotExist:
            return Response({
                'error': 'Genre not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to retrieve movies for genre {pk}: {str(e)}")
            return Response({
                'error': 'Failed to retrieve movies for genre',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class MovieSearchView(APIView):
    """
    Advanced search functionality for movies.
    Supports complex queries and filters.
    """
    
    def get(self, request):
        """
        Search movies with advanced filters.
        GET /api/search/?q=batman&genre=Action&year=2020&rating_min=7.0
        """
        query = request.query_params.get('q', '')
        genre = request.query_params.get('genre', '')
        year = request.query_params.get('year', '')
        rating_min = request.query_params.get('rating_min', '')
        rating_max = request.query_params.get('rating_max', '')
        
        # Start with all movies
        movies = Movie.objects.select_related().prefetch_related('genres')
        
        # Apply search query
        if query:
            movies = movies.filter(
                Q(title__icontains=query) | 
                Q(overview__icontains=query) |
                Q(director__icontains=query)
            )
        
        # Apply filters
        if genre:
            movies = movies.filter(genres__name__iexact=genre)
        
        if year:
            movies = movies.filter(release_date__year=year)
        
        if rating_min:
            movies = movies.filter(tmdb_rating__gte=float(rating_min))
        
        if rating_max:
            movies = movies.filter(tmdb_rating__lte=float(rating_max))
        
        # Order by relevance (popularity and rating)
        movies = movies.order_by('-popularity_score', '-tmdb_rating').distinct()
        
        # Paginate results
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(movies, request)
        if page is not None:
            serializer = MovieSearchSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = MovieSearchSerializer(movies, many=True)
        return Response(serializer.data)

class MovieRecommendationView(APIView):
    """
    Movie recommendation engine
    This one provides personalized movie recommendations based on user preferences.
    """
    @method_decorator(cache_page(60*15))  # Cache for 15 minutes
    def get(self, request):
        user_id = request.query_params.get('user_id')
        limit = int(request.query_params.get('limit', 10))
        rec_type = request.query_params.get('type', 'popular')

        if rec_type not in ['popular', 'top_rated', 'recent']:
            return Response({"detail": "Invalid recommendation type."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch recommendations based on the type
        if rec_type == 'popular':
            recommendations = self._get_popular_recommendations(limit)
        elif rec_type == 'top_rated':
            recommendations = self._get_top_rated_recommendations(limit)
        elif rec_type == 'recent':
            recommendations = self._get_recent_recommendations(limit)
        else:
            recommendations = self._get_popular_recommendations(limit)
        # Add recommendations metadata
        for movie in recommendations:
            movie.recommendation_score = movie.uniform(0.8, 0.99)
            movie_recommendation_reason = self._get_recommendation_reason(movie, user_id)

        serializer = MovieListSerializer(recommendations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def _get_popular_recommendations(self, limit):
        """Get recommendations based on popularity."""
        return Movie.objects.order_by('-popularity_score')[:limit]
    
    def _get_top_rated_recommendations(self, limit):
        """Get recommendations based on ratings."""
        return (Movie.objects
                .filter(tmdb_rating__gte=7.0)
                .order_by('-tmdb_rating')[:limit])
    
    def _get_random_recommendations(self, limit):
        """Get random movie recommendations."""
        return Movie.objects.order_by('?')[:limit]
    
    def _get_recommendation_reason(self, movie, rec_type):
        """Generate a reason for the recommendation."""
        reasons = {
            'popular': f"Trending with {movie.views} views",
            'top_rated': f"Highly rated ({movie.tmdb_rating}/10)",
            'random': "Discover something new",
        }
        return reasons.get(rec_type, "Recommended for you")


class MovieAnalyticsView(APIView):
    """
    Analytics and insights about movies.
    Useful for dashboard and reporting.
    """
    
    def get(self, request):
        """
        Get comprehensive movie analytics.
        GET /api/analytics/
        """
        # Check cache first
        cache_key = 'movie_analytics_data'
        analytics_data = cache.get(cache_key)
        
        if not analytics_data:
            analytics_data = {
                'overview': self._get_overview_stats(),
                'genre_breakdown': self._get_genre_breakdown(),
                'rating_distribution': self._get_rating_distribution(),
                'yearly_releases': self._get_yearly_releases(),
                'top_performers': self._get_top_performers(),
            }
            # Cache for 1 hour
            cache.set(cache_key, analytics_data, 3600)
        
        return Response(analytics_data)
    
    def _get_overview_stats(self):
        """Get basic overview statistics."""
        return {
            'total_movies': Movie.objects.count(),
            'total_genres': Genre.objects.count(),
            'avg_rating': round(Movie.objects.aggregate(avg=Avg('tmdb_rating'))['avg'] or 0, 2),
            'total_views': Movie.objects.aggregate(total=models.Sum('views'))['total'] or 0,
            'total_likes': Movie.objects.aggregate(total=models.Sum('like_count'))['total'] or 0,
        }
    
    def _get_genre_breakdown(self):
        """Get movie count by genre."""
        return list(Genre.objects
                   .annotate(movie_count=Count('movies'))
                   .order_by('-movie_count')
                   .values('name', 'movie_count')[:10])
    
    def _get_rating_distribution(self):
        """Get distribution of movie ratings."""
        # This is a simplified version - you might want more sophisticated bucketing
        ranges = [
            (0, 3), (3, 5), (5, 7), (7, 8), (8, 9), (9, 10)
        ]
        distribution = []
        
        for min_rating, max_rating in ranges:
            count = Movie.objects.filter(
                tmdb_rating__gte=min_rating,
                tmdb_rating__lt=max_rating
            ).count()
            distribution.append({
                'range': f"{min_rating}-{max_rating}",
                'count': count
            })
        
        return distribution
    
    def _get_yearly_releases(self):
        """Get movie releases by year."""
        from django.db.models import Extract
        return list(Movie.objects
                   .annotate(year=Extract('release_date', 'year'))
                   .values('year')
                   .annotate(count=Count('id'))
                   .order_by('-year')[:10])
    
    def _get_top_performers(self):
        """Get top performing movies by different metrics."""
        return {
            'most_viewed': list(Movie.objects.order_by('-views')[:5]
                              .values('title', 'views')),
            'most_liked': list(Movie.objects.order_by('-like_count')[:5]
                             .values('title', 'like_count')),
            'highest_rated': list(Movie.objects.order_by('-tmdb_rating')[:5]
                                .values('title', 'tmdb_rating')),
        }