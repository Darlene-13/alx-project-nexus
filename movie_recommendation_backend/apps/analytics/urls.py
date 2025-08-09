from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    analytics_hub,
    UserActivityLogViewSet,
    PopularityMetricsViewSet,
    TrendingMoviesView,
)

# App namespace for URL reversing
app_name = 'analytics'

# DRF Router for ViewSet endpoints
router = DefaultRouter()
router.register(r'activity-logs', UserActivityLogViewSet, basename='activitylog')
router.register(r'popularity-metrics', PopularityMetricsViewSet, basename='popularitymetrics')

urlpatterns = [
    # Analytics hub - landing page
    path('', analytics_hub, name='analytics-hub'),
    
    # Main API endpoints via router
    path('api/v1/', include(router.urls)),
    
    # Additional endpoints that aren't part of viewsets
    path('api/v1/trending/', TrendingMoviesView.as_view(), name='trending-movies'),
]