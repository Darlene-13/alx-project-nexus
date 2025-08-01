# recommendations/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Define URL patterns for the recommendations app
urlpatterns = [
    
    # === USER INTERACTION ENDPOINTS ===
    
    # List user's interactions or create new interaction
    path('interactions/', 
         views.UserInteractionListCreateView.as_view(), 
         name='user-interactions'),
    
    # Get, update, or delete specific interaction
    path('interactions/<int:pk>/', 
         views.UserInteractionDetailView.as_view(), 
         name='interaction-detail'),
    
    # Get all interactions for a specific movie
    path('movies/<int:movie_id>/interactions/', 
         views.MovieInteractionsView.as_view(), 
         name='movie-interactions'),
    
    # Quick interaction endpoint (for mobile apps)
    path('interactions/quick/', 
         views.quick_interaction, 
         name='quick-interaction'),
    
    
    # === RECOMMENDATION ENDPOINTS ===
    
    # Get user's personalized recommendations
    path('recommendations/', 
         views.UserRecommendationsView.as_view(), 
         name='user-recommendations'),
    
    # Create individual recommendation manually
    path('recommendations/create/', 
         views.UserRecommendationCreateView.as_view(), 
         name='create-recommendation'),
    
    # Track recommendation clicks
    path('recommendations/<int:recommendation_id>/click/', 
         views.RecommendationClickView.as_view(), 
         name='recommendation-click'),
    
    # Generate recommendations for current user
    path('recommendations/generate/', 
         views.GenerateRecommendationsView.as_view(), 
         name='generate-recommendations'),
    
    # Get recommendation feed with full movie details
    path('recommendations/feed/', 
         views.RecommendationFeedView.as_view(), 
         name='recommendation-feed'),
    
    
    # === ANALYTICS & PREFERENCES ENDPOINTS ===
    
    # Get user's preferences and behavior analytics
    path('preferences/', 
         views.UserPreferencesView.as_view(), 
         name='user-preferences'),
    
    # Get user's activity feed
    path('activity/', 
         views.UserActivityFeedView.as_view(), 
         name='user-activity'),
    
    # Get user's recommendation statistics
    path('stats/', 
         views.recommendation_stats, 
         name='recommendation-stats'),
    
    # Find users with similar preferences
    path('similar-users/', 
         views.SimilarUsersView.as_view(), 
         name='similar-users'),
    
    
    # === DISCOVERY & TRENDING ENDPOINTS ===
    
    # Get trending movies
    path('trending/', 
         views.TrendingMoviesView.as_view(), 
         name='trending-movies'),
    
    # Discover new movies based on preferences
    path('discover/', 
         views.discover_movies, 
         name='discover-movies'),
    
    
    # === ADMIN & ANALYTICS ENDPOINTS ===
    
    # Algorithm performance analytics (admin only)
    path('admin/performance/', 
         views.AlgorithmPerformanceView.as_view(), 
         name='algorithm-performance'),
    
    # Generate recommendations for all users (admin only)
    path('admin/generate-batch/', 
         views.GenerateBatchRecommendationsView.as_view(), 
         name='generate-batch-recommendations'),
    
    # Send recommendation notifications (admin only)
    path('admin/send-notifications/', 
         views.SendRecommendationNotificationsView.as_view(), 
         name='send-notifications'),
    
    # System cleanup (admin only)
    path('admin/cleanup/', 
         views.SystemCleanupView.as_view(), 
         name='system-cleanup'),
    
    # Find target users for specific movie (admin only)
    path('admin/movies/<int:movie_id>/targets/', 
         views.MovieRecommendationsView.as_view(), 
         name='movie-target-users'),
    
]

# App name for namespace
app_name = 'recommendations'