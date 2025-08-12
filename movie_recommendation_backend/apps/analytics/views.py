from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from django.utils import timezone
from django.shortcuts import render
from django.db import models
from django.db.models import Count, Sum, Avg, Q
from datetime import timedelta, datetime
import json

from .models import UserActivityLog, PopularityMetrics
from apps.movies.models import Movie
from apps.movies.serializers import MovieListSerializer
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
            {"method": "GET",    "url": "/analytics/api/v1/popularity-metrics/update_metrics/", "description": "Update all metrics manually",    "status": "✅ Active"},
        ],
        "🔥 TRENDING & INSIGHTS": [
            {"method": "GET",    "url": "/analytics/api/v1/trending/?days=7&limit=10",        "description": "Get trending movies",            "status": "✅ Active"},
            {"method": "GET",    "url": "/analytics/api/v1/analytics-summary/",               "description": "Platform analytics summary",     "status": "✅ Active"},
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
    queryset = UserActivityLog.objects.all().select_related('user', 'movie')
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserActivityLogCreateSerializer
        elif self.action == 'list':
            return UserActivityLogListSerializer
        elif self.action == 'retrieve':
            return UserActivityLogDetailSerializer
        return UserActivityLogDetailSerializer

    def get_queryset(self):
        """Optimize queryset and add filtering"""
        queryset = super().get_queryset()
        
        # Filter by user if requested
        user_id = self.request.query_params.get('user_id')
        if user_id:
            try:
                queryset = queryset.filter(user_id=int(user_id))
            except (ValueError, TypeError):
                pass
        
        # Filter by action type
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            try:
                days_int = int(days)
                cutoff_date = timezone.now() - timedelta(days=days_int)
                queryset = queryset.filter(timestamp__gte=cutoff_date)
            except (ValueError, TypeError):
                pass
        
        return queryset

    def perform_create(self, serializer):
        """
        Auto-assign user and metadata fields from request.
        """
        serializer.save(
            user=self.request.user if self.request.user.is_authenticated else None,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            referer=self.request.META.get('HTTP_REFERER'),
        )

    @action(detail=False, methods=['post'], url_path='bulk_log')
    def bulk_log(self, request):
        """
        Log multiple activities in a single request.
        Example: POST /analytics/api/v1/activity-logs/bulk_log/
        """
        serializer = BulkActivityLogSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                "message": "Activities logged successfully",
                "created_count": result["created_count"],
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='analytics_summary')
    def analytics_summary(self, request):
        """
        Return summary of user's activity.
        Example: GET /analytics/api/v1/activity-logs/analytics_summary/
        """
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        activities = UserActivityLog.objects.filter(user=user)
        
        if not activities.exists():
            return Response({
                "message": "No activity found for this user",
                "total_activities": 0
            })

        # Calculate various metrics
        activity_counts = activities.values('action_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Get most viewed movies
        most_viewed_movies = activities.filter(
            action_type='movie_view',
            movie__isnull=False
        ).values('movie__title').annotate(
            views=Count('id')
        ).order_by('-views')[:5]

        summary_data = {
            "user_id": user.id,
            "username": user.username,
            "total_activities": activities.count(),
            "movie_views": activities.filter(action_type='movie_view').count(),
            "ratings_given": activities.filter(action_type='rating_submit').count(),
            "favorites_added": activities.filter(action_type='favorite_add').count(),
            "watchlist_additions": activities.filter(action_type='watchlist_add').count(),
            "last_activity": activities.latest('timestamp').timestamp if activities.exists() else None,
            "activity_breakdown": list(activity_counts),
            "most_viewed_movies": list(most_viewed_movies),
            "engagement_level": "high" if activities.count() > 50 else "medium" if activities.count() > 10 else "low"
        }

        return Response(summary_data)

    @action(detail=False, methods=['get'], url_path='sessions')
    def session_analytics(self, request):
        """
        Return session-based behavioral data.
        Example: GET /analytics/api/v1/activity-logs/sessions/?session_id=sess_123
        """
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({"detail": "session_id parameter is required"}, status=400)

        activities = UserActivityLog.objects.filter(session_id=session_id).order_by('timestamp')
        if not activities.exists():
            return Response({"detail": "No activity found for this session."}, status=404)

        start = activities.first().timestamp
        end = activities.last().timestamp
        duration = (end - start).total_seconds() / 60

        # Analyze conversion events
        conversion_events = activities.filter(action_type__in=[
            'rating_submit', 'favorite_add', 'watchlist_add'
        ]).values_list('action_type', flat=True)

        data = {
            "session_id": session_id,
            "user": activities.first().user.username if activities.first().user else "Anonymous",
            "start_time": start,
            "end_time": end,
            "duration_minutes": round(duration, 2),
            "activity_count": activities.count(),
            "unique_movies_viewed": activities.filter(movie__isnull=False).values('movie_id').distinct().count(),
            "conversion_events": list(conversion_events),
            "activity_timeline": list(activities.values('action_type', 'timestamp', 'movie__title'))
        }

        return Response(data)


class PopularityMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for viewing popularity metrics of movies.
    """
    queryset = PopularityMetrics.objects.select_related('movie').order_by('-date', '-view_count')
    serializer_class = PopularityMetricsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Add filtering options"""
        queryset = super().get_queryset()
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            try:
                days_int = int(days)
                cutoff_date = timezone.now().date() - timedelta(days=days_int)
                queryset = queryset.filter(date__gte=cutoff_date)
            except (ValueError, TypeError):
                pass
        
        # Filter by minimum view count
        min_views = self.request.query_params.get('min_views')
        if min_views:
            try:
                queryset = queryset.filter(view_count__gte=int(min_views))
            except (ValueError, TypeError):
                pass
        
        return queryset

    @action(detail=False, methods=['post'], url_path='update_metrics')
    def update_metrics(self, request):
        """
        Manually trigger popularity metrics update for all movies.
        Example: POST /analytics/api/v1/popularity-metrics/update_metrics/
        """
        try:
            from datetime import date
            updated_count = 0
            
            # Update metrics for all movies for today
            movies = Movie.objects.all()
            for movie in movies:
                PopularityMetrics.update_daily_metrics(movie, date.today())
                updated_count += 1
            
            return Response({
                'message': f'Updated popularity metrics for {updated_count} movies',
                'date': date.today(),
                'updated_count': updated_count
            })
        except Exception as e:
            return Response({
                'error': f'Failed to update metrics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrendingMoviesView(generics.ListAPIView):
    """
    Return trending movies based on recent popularity.
    Example: GET /analytics/api/v1/trending/?days=7&limit=10
    """
    serializer_class = MovieListSerializer  # Use Movie serializer, not custom trending one
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Get trending movies with proper error handling"""
        try:
            # Get and validate parameters
            days = int(self.request.query_params.get('days', 7))
            limit = int(self.request.query_params.get('limit', 10))
            
            # Ensure reasonable bounds
            days = max(1, min(days, 365))  # 1 day to 1 year
            limit = max(1, min(limit, 100))  # 1 to 100 movies
            
        except (ValueError, TypeError):
            # Fallback to defaults if parameters are invalid
            days = 7
            limit = 10
        
        # Get trending data from PopularityMetrics
        trending_data = PopularityMetrics.get_trending_movies(days=days, limit=limit)
        
        if not trending_data:
            # If no trending data, return recent movies with high ratings
            return Movie.objects.filter(
                tmdb_rating__gte=7.0
            ).order_by('-release_date', '-tmdb_rating')[:limit]
        
        # Extract movie IDs from trending data
        movie_ids = [item['movie'] for item in trending_data]
        
        # Get actual Movie objects, preserving the trending order
        movies = Movie.objects.filter(id__in=movie_ids)
        
        # Create a dictionary for quick lookup
        movie_dict = {movie.id: movie for movie in movies}
        
        # Return movies in trending order
        ordered_movies = []
        for item in trending_data:
            movie_id = item['movie']
            if movie_id in movie_dict:
                movie = movie_dict[movie_id]
                # Add trending metadata to the movie object
                movie.trending_views = item.get('total_views', 0)
                movie.trending_likes = item.get('total_likes', 0)
                movie.trending_rating = item.get('average_rating', 0)
                ordered_movies.append(movie)
        
        return ordered_movies

    def list(self, request, *args, **kwargs):
        """Override list to add trending metadata"""
        queryset = self.get_queryset()
        
        # Check if we have any data
        if not queryset:
            return Response({
                'count': 0,
                'results': [],
                'message': 'No trending data available. Try running the analytics seeder to generate test data.'
            })
        
        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)
        
        # Add trending metadata to response
        data = serializer.data
        for i, movie_data in enumerate(data):
            if i < len(queryset):
                movie = queryset[i]
                movie_data['trending_metadata'] = {
                    'views': getattr(movie, 'trending_views', 0),
                    'likes': getattr(movie, 'trending_likes', 0),
                    'avg_rating': getattr(movie, 'trending_rating', 0)
                }
        
        return Response({
            'count': len(data),
            'results': data
        })


class AnalyticsSummaryView(generics.GenericAPIView):
    """
    Platform-wide analytics summary.
    Example: GET /analytics/api/v1/analytics-summary/
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """Return comprehensive platform analytics"""
        try:
            # Date calculations
            now = timezone.now()
            today = now.date()
            yesterday = today - timedelta(days=1)
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            # Activity statistics
            activities_today = UserActivityLog.objects.filter(timestamp__date=today).count()
            activities_yesterday = UserActivityLog.objects.filter(timestamp__date=yesterday).count()
            activities_week = UserActivityLog.objects.filter(timestamp__date__gte=week_ago).count()
            activities_month = UserActivityLog.objects.filter(timestamp__date__gte=month_ago).count()

            # User engagement
            active_users_today = UserActivityLog.objects.filter(
                timestamp__date=today
            ).values('user').distinct().count()

            active_users_week = UserActivityLog.objects.filter(
                timestamp__date__gte=week_ago
            ).values('user').distinct().count()

            # Most popular actions
            top_actions = UserActivityLog.objects.filter(
                timestamp__date__gte=week_ago
            ).values('action_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5]

            # Top movies this week
            top_movies_week = PopularityMetrics.objects.filter(
                date__gte=week_ago
            ).values('movie__title').annotate(
                total_views=Sum('view_count')
            ).order_by('-total_views')[:5]

            # Growth calculation
            growth_rate = 0
            if activities_yesterday > 0:
                growth_rate = round(
                    ((activities_today - activities_yesterday) / activities_yesterday) * 100, 1
                )

            # Platform health metrics
            total_metrics = PopularityMetrics.objects.count()
            avg_engagement = PopularityMetrics.objects.aggregate(
                avg_views=Avg('view_count')
            )['avg_views'] or 0

            summary = {
                "platform_overview": {
                    "total_activities_today": activities_today,
                    "total_activities_yesterday": activities_yesterday,
                    "total_activities_week": activities_week,
                    "total_activities_month": activities_month,
                    "growth_rate_daily": growth_rate,
                },
                "user_engagement": {
                    "active_users_today": active_users_today,
                    "active_users_week": active_users_week,
                    "avg_activities_per_user": round(activities_week / max(active_users_week, 1), 1),
                },
                "content_performance": {
                    "total_popularity_metrics": total_metrics,
                    "avg_views_per_movie": round(avg_engagement, 1),
                    "top_movies_this_week": list(top_movies_week),
                },
                "activity_breakdown": {
                    "top_actions_this_week": list(top_actions),
                },
                "system_health": {
                    "data_freshness": "Good" if activities_today > 0 else "No recent data",
                    "metrics_coverage": f"{total_metrics} movies tracked",
                }
            }

            return Response(summary)

        except Exception as e:
            return Response({
                'error': f'Failed to generate analytics summary: {str(e)}',
                'suggestion': 'Make sure you have run the analytics seeder to generate test data.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)