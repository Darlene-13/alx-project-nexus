from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from django.utils import timezone
from django.shortcuts import render
from django.db import models

from .models import UserActivityLog, PopularityMetrics
from .serializers import (
    UserActivityLogCreateSerializer,
    UserActivityLogDetailSerializer,
    UserActivityLogListSerializer,
    BulkActivityLogSerializer,
    PopularityMetricsSerializer,
    TrendingMoviesSerializer,
    UserActivitySummarySerializer,
    SessionAnalyticsSerializer,
)

def analytics_hub(request):
    """Analytics app hub showing all available endpoints."""
    from django.shortcuts import render
    
    endpoints_by_section = {
        "📊 ACTIVITY LOGS": [
            {"method": "GET",    "url": "/analytics/api/v1/activity-logs/",                    "description": "List user activity logs",        "status": "✅ Active"},
            {"method": "POST",   "url": "/analytics/api/v1/activity-logs/",                    "description": "Create activity log",            "status": "✅ Active"},
            {"method": "GET",    "url": "/analytics/api/v1/activity-logs/{pk}/",              "description": "Get activity log details",       "status": "✅ Active"},
            {"method": "POST",   "url": "/analytics/api/v1/activity-logs/bulk_log/",          "description": "Bulk activity logging",          "status": "✅ Active"},
            {"method": "GET",    "url": "/analytics/api/v1/activity-logs/analytics_summary/", "description": "User activity summary",          "status": "✅ Active"},
            {"method": "GET",    "url": "/analytics/api/v1/activity-logs/sessions/",          "description": "Session analytics",              "status": "✅ Active"},
        ],
        "📈 POPULARITY METRICS": [
            {"method": "GET",    "url": "/analytics/api/v1/popularity-metrics/",              "description": "List popularity metrics",        "status": "✅ Active"},
            {"method": "GET",    "url": "/analytics/api/v1/popularity-metrics/{pk}/",        "description": "Get specific metric details",    "status": "✅ Active"},
        ],
        "🔥 TRENDING & INSIGHTS": [
            {"method": "GET",    "url": "/analytics/api/v1/trending/",                        "description": "Get trending movies",            "status": "✅ Active"},
        ],
        "📘 API DOCUMENTATION": [
            {"method": "GET", "url": "/analytics/docs/",   "description": "Swagger UI",   "status": "✅ Active"},
            {"method": "GET", "url": "/analytics/redoc/",  "description": "ReDoc UI",     "status": "✅ Active"},
            {"method": "GET", "url": "/analytics/schema/", "description": "Schema (JSON)", "status": "✅ Active"},
        ],
    }
    
    # Flatten the endpoints for the template
    flat_endpoints = []
    for section_name, section_endpoints in endpoints_by_section.items():
        for endpoint in section_endpoints:
            flat_endpoints.append(endpoint)
    
    context = {
        'app_name': '📊 Analytics API Hub',
        'app_description': 'Monitor user behavior, track engagement, and analyze movie trends',
        'endpoints': endpoints_by_section,
        'flat_endpoints': flat_endpoints,
    }
    
    return render(request, 'analytics/analytics_hub.html', context)

class UserActivityLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing UserActivityLog:
    - POST: create a new activity
    - GET: list user logs
    - /bulk_log/: bulk activity logging
    - /analytics_summary/: activity summaries
    - /sessions/: session-based behavior tracking
    """
    queryset = UserActivityLog.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserActivityLogCreateSerializer
        elif self.action == 'list':
            return UserActivityLogListSerializer
        elif self.action == 'retrieve':
            return UserActivityLogDetailSerializer
        return UserActivityLogDetailSerializer

    def perform_create(self, serializer):
        """
        Auto-assign user and metadata fields from request.
        """
        serializer.save(
            user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            referer=self.request.META.get('HTTP_REFERER'),
        )

    @action(detail=False, methods=['post'], url_path='bulk_log')
    def bulk_log(self, request):
        """
        Log multiple activities in a single request.
        """
        serializer = BulkActivityLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({
            "created_count": result["created_count"],
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='analytics_summary')
    def analytics_summary(self, request):
        """
        Return summary of user's activity.
        """
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        activities = UserActivityLog.objects.filter(user=user)
        summary_data = {
            "user": user,
            "total_activities": activities.count(),
            "movie_views": activities.filter(action_type='movie_view').count(),
            "ratings_given": activities.filter(action_type='rating_submit').count(),
            "favorites_added": activities.filter(action_type='favorite_add').count(),
            "watchlist_additions": activities.filter(action_type='watchlist_add').count(),
            "last_activity": activities.latest('timestamp').timestamp if activities.exists() else None,
            "most_active_day": activities.dates('timestamp', 'day').annotate(
                count=models.Count('id')
            ).order_by('-count').first(),
            "engagement_level": "medium"  # Placeholder, adjust logic as needed
        }

        serializer = UserActivitySummarySerializer(summary_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='sessions')
    def session_analytics(self, request):
        """
        Return session-based behavioral data.
        """
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({"detail": "session_id is required"}, status=400)

        activities = UserActivityLog.objects.filter(session_id=session_id)
        if not activities.exists():
            return Response({"detail": "No activity for this session."}, status=404)

        start = activities.earliest('timestamp').timestamp
        end = activities.latest('timestamp').timestamp
        duration = (end - start).total_seconds() / 60

        data = {
            "session_id": session_id,
            "user": activities.first().user,
            "start_time": start,
            "end_time": end,
            "duration_minutes": round(duration, 2),
            "activity_count": activities.count(),
            "unique_movies_viewed": activities.values('movie_id').distinct().count(),
            "conversion_events": list(activities.filter(action_type__in=[
                'rating_submit', 'favorite_add', 'watchlist_add'
            ]).values_list('action_type', flat=True).distinct())
        }

        serializer = SessionAnalyticsSerializer(data)
        return Response(serializer.data)


class PopularityMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for viewing popularity metrics of movies.
    """
    queryset = PopularityMetrics.objects.select_related('movie')
    serializer_class = PopularityMetricsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class TrendingMoviesView(generics.ListAPIView):
    """
    Return trending movies based on recent popularity.
    """
    serializer_class = TrendingMoviesSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        days = int(self.request.query_params.get('days', 7))
        limit = int(self.request.query_params.get('limit', 10))
        return PopularityMetrics.get_trending_movies(days=days, limit=limit)
