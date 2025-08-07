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
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from .models import Movie, Genre, MovieGenre
from.serializers import (
    MovieListSerializer, MovieDetailSerializer, MovieCreateUpdateSerializer,
    MovieStatsSerializer, MovieSearchSerializer, MovieRecommendationSerializer,
    GenreSerializer, GenreDetailSerializer, MovieGenreSerializer

)

from .filters import MovieFilter

class StandardResultsSetPagination(PageNumberPagination):

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
    pagination_class = StandardResultsSetPagination
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
        """
        limit = request.query_params.get('limit', 10)
        movies = self.get_queryset().order_by('-popularity_score')[:limit]
        serializer = self.get_serializer(movies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)