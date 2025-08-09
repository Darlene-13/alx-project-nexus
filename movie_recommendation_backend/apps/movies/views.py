"""
This is our movie recommendation views file for the movies app.
It contains views for our movie models.
Includes different views for listing, creating, updating, and deleting movies.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination


from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F, Count, Avg
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db import models

from .models import Movie, Genre, MovieGenre
from .serializers import (
    MovieListSerializer, MovieDetailSerializer, MovieCreateUpdateSerializer,
    MovieStatsSerializer, MovieRecommendationSerializer,
    GenreSerializer, GenreDetailSerializer, MovieSearchSerializer
)

from .filters import MovieFilter

from django.shortcuts import render

def movie_hub(request):
    """Movies app hub showing all available endpoints, grouped by section."""

    endpoints_by_section = {
        "🎬 MOVIES": [
            {"method": "GET",    "url": "/movies/api/v1/movies/",                  "description": "List all movies",       "status": "✅ Active"},
            {"method": "POST",   "url": "/movies/api/v1/movies/",                  "description": "Create a new movie",     "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/movies/{pk}/",            "description": "Retrieve movie details", "status": "✅ Active"},
            {"method": "PUT",    "url": "/movies/api/v1/movies/{pk}/",            "description": "Update movie",           "status": "✅ Active"},
            {"method": "PATCH",  "url": "/movies/api/v1/movies/{pk}/",            "description": "Partial update",         "status": "✅ Active"},
            {"method": "DELETE", "url": "/movies/api/v1/movies/{pk}/",            "description": "Delete movie",           "status": "✅ Active"},
        ],
        "🎯 MOVIE CUSTOM ACTIONS": [
            {"method": "GET",    "url": "/movies/api/v1/movies/popular/",                     "description": "Popular movies",       "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/movies/top_rated/",                   "description": "Top-rated movies",     "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/movies/recent/",                      "description": "Recently released",    "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/movies/by_genre/?genre=Action",       "description": "Movies by genre",      "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/movies/stats/",                       "description": "Movie stats",          "status": "✅ Active"},
            {"method": "POST",   "url": "/movies/api/v1/movies/{pk}/increment_views/",        "description": "Increment views",      "status": "✅ Active"},
            {"method": "POST",   "url": "/movies/api/v1/movies/{pk}/increment_likes/",        "description": "Increment likes",      "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/movies/{pk}/similar/",                "description": "Similar movies",       "status": "✅ Active"},
        ],
        "📚 GENRES": [
            {"method": "GET",    "url": "/movies/api/v1/genres/",                  "description": "List genres",             "status": "✅ Active"},
            {"method": "POST",   "url": "/movies/api/v1/genres/",                  "description": "Create genre",            "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/genres/{pk}/",            "description": "Genre details",           "status": "✅ Active"},
            {"method": "PUT",    "url": "/movies/api/v1/genres/{pk}/",            "description": "Update genre",            "status": "✅ Active"},
            {"method": "PATCH",  "url": "/movies/api/v1/genres/{pk}/",            "description": "Partial update",          "status": "✅ Active"},
            {"method": "DELETE", "url": "/movies/api/v1/genres/{pk}/",            "description": "Delete genre",            "status": "✅ Active"},
            {"method": "GET",    "url": "/movies/api/v1/genres/{pk}/movies/",     "description": "Movies in genre",         "status": "✅ Active"},
        ],
        "🔎 SEARCH & RECOMMENDATIONS": [
            {"method": "GET", "url": "/movies/api/v1/search/?q=batman",             "description": "Advanced search",         "status": "✅ Active"},
            {"method": "GET", "url": "/movies/api/v1/recommendations/?type=popular","description": "Recommendations",         "status": "✅ Active"},
        ],
        "📊 ANALYTICS": [
            {"method": "GET", "url": "/movies/api/v1/analytics/",                  "description": "Analytics overview",      "status": "✅ Active"},
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
    THis is a vieset for CRUD operations in the movie model.
    """
    queryset = Movie.objects.select_related().prefetch_related('genres')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MovieFilter # Custom filter class for movies
    ordering_fields = ['release_date', 'popularity_score', 'tmdb_rating', 'popularity_score', 'views', 'like_count']
    ordering = ['-release_date']  # Default ordering by release date

    def get_serializer_class(self):
        """
        It returns the appropriate serializer class based on the action.
        """
        if self.action == 'list':
            return MovieListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return MovieCreateUpdateSerializer
        elif self.action == 'stats':
            return MovieStatsSerializer
        elif self.action == 'recommendations':
            return MovieRecommendationSerializer
        return MovieDetailSerializer
    

    def get_queryset(self):
        """
        It returns the queryset for the viewset.
        """
        queryset = Movie.objects.select_related.prefetch_related('genres')

        # Application of different optimization based on acction
        if self.action == 'list':
            queryset = queryset.defer('overview', 'tagline')

        return queryset
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """
        Get popular movies based on popularity score.
        Example: /api/movies/popular/?limit=10
        """
        limit = request.query_params.get('limit', 10)
        movies = self.get_queryset().order_by('-popularity_score')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """
        Get top-rated movies based on TMDB rating.
        Example: /api/movies/top_rated/?min_rating=7.0&limit=10
        """
        min_rating = float(request.query_params.get('min_rating', 7.0))
        limit = request.query_params.get('limit', 10)
        movies = self.get_queryset().filter(tmdb_rating__gte=min_rating).order_by('-tmdb_rating')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent movies based on release date.
        Example: /api/movies/recent/?limit=10
        """
        limit = request.query_params.get('limit', 10)
        movies = self.get_queryset().order_by('-release_date')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def by_genre(self, request):
        """
        Get movies by genre.
        Example: /api/movies/by_genre/?genre=Action&limit=10
        """
        genre_name = request.query_params.get('genre')
        if not genre_name:
            return Response({"detail": "Genre name is required."}, status=status.HTTP_400_BAD_REQUEST)

        limit = request.query_params.get('limit', 10)
        movies = self.get_queryset().filter(genres__name=genre_name).order_by('-release_date')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """
        Increment the view count for a movie.
        Example: /api/movies/{id}/increment_views/
        """
        movie = self.get_object()
        Movie.objects.filter(id=movie.id).update(views=F('views') + 1)
        movie.refresh_from_db()
        return Response(
            {'views': movie.views}
        )
    

    @action(detail=True, methods=['post'])
    def increment_likes(self, request, pk=None):
        """
        Increment the like count for a movie.
        Example: /api/movies/{id}/increment_likes/
        """
        movie = self.get_object()
        Movie.objects.filter(id=movie.id).update(like_count=F('like_count') + 1)
        movie.refresh_from_db()
        return Response(
            {'likes': movie.like_count}
        )
    

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """
        Get similar movies based on genres.
        Example: /api/movies/{id}/similar/
        """
        movie = self.get_object()
        limit = int(request.query_params.get('limit', 10))
        similar_movies = (
            Movie.objects.filter(genres__in=movie.genres.all()).exclude(id=movie.id).
            annotate(genre_matches=Count('genres')).order_by('-genre_matches', '-tmdb_rating').
            distinct()[:limit]
        )
        serializer = MovieListSerializer(similar_movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get the statistics of movies.
        Example: /api/movies/stats/
        """
        stats = {
            'total_movies': Movie.objects.count(),
            'avg_rating': Movie.objects.aggregate(avg=Avg('tmdb_rating'))['avg'],
            'total_views': Movie.objects.aggregate(total=models.Sum('views'))['total'] or 0,  # Fixed: added "or 0"
            'total_likes': Movie.objects.aggregate(total=models.Sum('like_count'))['total'] or 0,  # Added this
            'top_genres': list(Genre.objects.annotate(
                movie_count=Count('movies')
            ).order_by('-movie_count')[:10]
            .values('name', 'movie_count'))  # Fixed: moved outside annotate
        }
        return Response(stats, status=status.HTTP_200_OK)


class GenreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations in the Genre model.

    """
    queryset = Genre.objects.all()
    permission_classes = [
        IsAuthenticatedOrReadOnly
    ]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the action.
        """
        if self.action == 'list':
            return GenreDetailSerializer
        return GenreSerializer

    @action(detail=True, methods=['get'])
    def movies(self, request, pk=None):
        """
        Gets all movies associated with a certain genre.
        Example: /api/genres/{id}/movies/
        """
        genre = self.get_object()
        movies = genre.movies.all()

        # Apply pagination
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(movies, request)
        if page is not None:
            serializer = MovieListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = MovieListSerializer(movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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