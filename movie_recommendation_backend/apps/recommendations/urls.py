from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns

from .views import (
    UserMovieInteractionViewSet,
    UserRecommendationViewSet,
    RecommendationExperimentViewSet,
    UserProfileViewSet,
    AnalyticsViewSet,
    RecommendationUtilityViewSet,
    recommendations_hub
)

app_name = 'recommendations'

# Custom UserProfileViewSet endpoints
user_profile_list = UserProfileViewSet.as_view({'get': 'me'})
user_profile_update = UserProfileViewSet.as_view({'patch': 'update_preferences'})
user_onboarding = UserProfileViewSet.as_view({'post': 'onboarding'})
user_genre_preference = UserProfileViewSet.as_view({'post': 'add_genre_preference'})
user_recommendation_context = UserProfileViewSet.as_view({'get': 'recommendation_context'})
user_reset_preferences = UserProfileViewSet.as_view({'post': 'reset_preferences'})

urlpatterns = [
    # Recommendations hub landing page
    path('', recommendations_hub, name='recommendations-hub'),

    # API v1 endpoints
    # User Movie Interactions
    path('v1/interactions/', include([
        path('', UserMovieInteractionViewSet.as_view({'get': 'list', 'post': 'create'}), name='interaction-list'),
        path('<int:pk>/', UserMovieInteractionViewSet.as_view({
            'get': 'retrieve', 
            'put': 'update', 
            'patch': 'partial_update', 
            'delete': 'destroy'
        }), name='interaction-detail'),
        path('my_interactions/', UserMovieInteractionViewSet.as_view({'get': 'my_interactions'}), name='my-interactions'),
        path('bulk_create/', UserMovieInteractionViewSet.as_view({'post': 'bulk_create'}), name='interaction-bulk-create'),
        path('analytics/', UserMovieInteractionViewSet.as_view({'get': 'analytics'}), name='interaction-analytics'),
        path('<int:pk>/update_feedback/', UserMovieInteractionViewSet.as_view({'patch': 'update_feedback'}), name='interaction-update-feedback'),
    ])),

    # User Recommendations
    path('v1/recommendations/', include([
        path('', UserRecommendationViewSet.as_view({'get': 'list'}), name='recommendation-list'),
        path('<int:pk>/', UserRecommendationViewSet.as_view({'get': 'retrieve'}), name='recommendation-detail'),
        path('personalized/', UserRecommendationViewSet.as_view({'get': 'personalized'}), name='personalized-recommendations'),
        path('performance/', UserRecommendationViewSet.as_view({'get': 'performance'}), name='recommendation-performance'),
        path('<int:pk>/click/', UserRecommendationViewSet.as_view({'post': 'click'}), name='recommendation-click'),
        path('bulk_click/', UserRecommendationViewSet.as_view({'post': 'bulk_click'}), name='recommendation-bulk-click'),
    ])),

    # Recommendation Experiments
    path('v1/experiments/', include([
        path('', RecommendationExperimentViewSet.as_view({'get': 'list', 'post': 'create'}), name='experiment-list'),
        path('<int:pk>/', RecommendationExperimentViewSet.as_view({
            'get': 'retrieve', 
            'put': 'update', 
            'patch': 'partial_update', 
            'delete': 'destroy'
        }), name='experiment-detail'),
        path('active/', RecommendationExperimentViewSet.as_view({'get': 'active'}), name='active-experiment'),
        path('<int:pk>/stop/', RecommendationExperimentViewSet.as_view({'post': 'stop'}), name='experiment-stop'),
        path('<int:pk>/metrics/', RecommendationExperimentViewSet.as_view({'get': 'metrics'}), name='experiment-metrics'),
        path('<int:pk>/update_results/', RecommendationExperimentViewSet.as_view({'post': 'update_results'}), name='experiment-update-results'),
    ])),

    # User Profile Management
    path('v1/users/', include([
        path('me/', user_profile_list, name='user-profile'),
        path('update_preferences/', user_profile_update, name='user-update-preferences'),
        path('onboarding/', user_onboarding, name='user-onboarding'),
        path('add_genre_preference/', user_genre_preference, name='user-add-genre-preference'),
        path('recommendation_context/', user_recommendation_context, name='user-recommendation-context'),
        path('reset_preferences/', user_reset_preferences, name='user-reset-preferences'),
    ])),

    # Analytics Endpoints
    path('v1/analytics/', include([
        path('dashboard/', AnalyticsViewSet.as_view({'get': 'dashboard'}), name='analytics-dashboard'),
        path('algorithm_performance/', AnalyticsViewSet.as_view({'get': 'algorithm_performance'}), name='analytics-algorithm-performance'),
        path('user_segmentation/', AnalyticsViewSet.as_view({'get': 'user_segmentation'}), name='analytics-user-segmentation'),
    ])),

    # Utility Endpoints
    path('v1/utils/', include([
        path('generate_recommendations/', RecommendationUtilityViewSet.as_view({'post': 'generate_recommendations'}), name='utils-generate-recommendations'),
        path('health/', RecommendationUtilityViewSet.as_view({'get': 'health'}), name='utils-health'),
    ])),

    # Optional: Browsable API login/logout
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

# Optional: Suffix support like `.json`, `.xml`
urlpatterns = format_suffix_patterns(urlpatterns)