"""
This is the URL configuration for the movies app in the movie recommendation backend.
The urls are defined based on our views.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from . import views
from .views import (movie_hub,
                    MovieSearchView,
                    MovieRecommendationView,
                    MovieAnalyticsView
                    )


# Create router for ViewSets
router = DefaultRouter()
router.register(r'movies', views.MovieViewSet, basename='movie')
router.register(r'genres', views.GenreViewSet, basename='genre')

# Custom URL patterns for specific endpoints
urlpatterns = [
    # Include router URLs
    path('movies/', include(router.urls)),

    path('hub/', movie_hub, name='movie-hub'),

    # Custom search and recommendsation endpoints
    path('search/', views.MovieSearchView.as_view(), name='movie-search'),
    path('recommendations/', views.MovieRecommendationView.as_view(), name='movie-recommendations'),
    path('analytics/', views.MovieAnalyticsView.as_view(), name='movie-analytics'),
]

"""
This configuration provides the following endpoints:

MOVIES:
GET    /api/movies/                    - List all movies (paginated, filtered, searchable)
POST   /api/movies/                    - Create a new movie
GET    /api/movies/{id}/               - Get movie details
PUT    /api/movies/{id}/               - Update movie
PATCH  /api/movies/{id}/               - Partial update movie
DELETE /api/movies/{id}/               - Delete movie

MOVIE CUSTOM ACTIONS:
GET    /api/movies/popular/            - Get popular movies
GET    /api/movies/top_rated/          - Get top-rated movies
GET    /api/movies/recent/             - Get recently released movies
GET    /api/movies/by_genre/           - Get movies by genre
GET    /api/movies/stats/              - Get movie statistics
POST   /api/movies/{id}/increment_views/ - Increment view count
POST   /api/movies/{id}/increment_likes/ - Increment like count
GET    /api/movies/{id}/similar/       - Get similar movies

GENRES:
GET    /api/genres/                    - List all genres
POST   /api/genres/                    - Create a new genre
GET    /api/genres/{id}/               - Get genre details
PUT    /api/genres/{id}/               - Update genre
PATCH  /api/genres/{id}/               - Partial update genre
DELETE /api/genres/{id}/               - Delete genre
GET    /api/genres/{id}/movies/        - Get all movies for a genre

SEARCH & RECOMMENDATIONS:
GET    /api/search/                    - Advanced movie search
GET    /api/recommendations/           - Get movie recommendations

ANALYTICS:
GET    /api/analytics/                 - Get comprehensive analytics data

FILTERING EXAMPLES:
GET /api/movies/?tmdb_rating_gte=8.0&release_year=2023&genre_name=Action
GET /api/movies/?search=batman&runtime_gte=120&adult=false
GET /api/movies/?popularity_gte=50&rating_range=7.0,9.0&year_range=2020,2023
GET /api/movies/?ordering=-tmdb_rating&page_size=50
"""