from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# App namespace for URL reversing
app_name = 'analytics'

# DRF Router for ViewSet endpoints
router = DefaultRouter()
router.register(r'activity-logs', views.UserActivityLogViewSet, basename='activitylog')
router.register(r'popularity-metrics', views.PopularityMetricsViewSet, basename='popularitymetrics')

urlpatterns = [
    # Main API endpoints via router
    path('api/', include(router.urls)),
    
    # Quick access endpoints (convenience URLs)
    path('log/', views.UserActivityLogViewSet.as_view({'post': 'log_activity'}), name='quick-log'),
    path('trending/', views.PopularityMetricsViewSet.as_view({'get': 'trending'}), name='trending'),
    path('analytics/', views.UserActivityLogViewSet.as_view({'get': 'analytics'}), name='analytics'),
]