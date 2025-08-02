from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserActivityLog, PopularityMetrics

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user serializer for nested representations.
    
    DESIGN DECISION: Only includes safe, public fields to avoid exposing sensitive data
    like email, password, etc. This is used when we need user info in nested objects.
    
    WHY ModelSerializer: Since we're dealing with a Django model and want standard
    field validation and representation.
    """
    class Meta:
        model = User
        fields = ['id', 'username']
        read_only_fields = ['id', 'username']  # These should never be modified via nested serializer


class MovieBasicSerializer(serializers.ModelSerializer):
    """
    Basic movie serializer for nested representations.
    
    NAMING CONVENTION: "Basic" suffix indicates this is a lightweight version
    used for nested relationships, not standalone operations.
    
    STRING REFERENCE: Using string reference 'movies.Movie' instead of importing
    to avoid circular import issues between apps.
    """
    class Meta:
        model = 'movies.Movie'  
        fields = ['id', 'title', 'slug']
        read_only_fields = ['id', 'title', 'slug']


class UserActivityLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating activity logs.
    
    DESIGN PHILOSOPHY: Optimized for write operations with minimal friction.
    The client should be able to log activities quickly without complex payload.
    
    KEY DECISIONS:
    1. Custom 'metadata_dict' field for easier JSON handling
    2. Most fields are optional to reduce API complexity
    3. User field NOT included - set automatically from request context
    4. IP, user_agent etc. captured automatically in view
    """
    
    # Custom field to handle metadata as dict instead of raw JSON string
    metadata_dict = serializers.JSONField(
        required=False, 
        write_only=True,
        help_text="Metadata as JSON object. Will be converted to string internally."
    )
    
    class Meta:
        model = UserActivityLog
        fields = [
            'session_id', 'action_type', 'movie', 'ip_address', 
            'user_agent', 'referer', 'source', 'metadata_dict'
        ]
        
        # SECURITY: These fields are optional because they'll be auto-populated
        # from request context in the view. Client shouldn't manually set them.
        extra_kwargs = {
            'ip_address': {'required': False, 'help_text': 'Auto-detected if not provided'},
            'user_agent': {'required': False, 'help_text': 'Auto-detected if not provided'},
            'referer': {'required': False, 'help_text': 'Auto-detected if not provided'},
            'source': {'required': False, 'default': 'api'},
        }

    def create(self, validated_data):
        """
        Custom create method to handle metadata_dict conversion.
        
        WHY CUSTOM CREATE: The model expects metadata as JSON string,
        but API consumers prefer to send JSON objects. This bridges that gap.
        """
        metadata_dict = validated_data.pop('metadata_dict', None)
        instance = UserActivityLog.objects.create(**validated_data)
        
        if metadata_dict:
            instance.set_metadata_dict(metadata_dict)
            instance.save()
            
        return instance


class UserActivityLogDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for reading activity logs.
    
    DESIGN PHILOSOPHY: Comprehensive representation for detailed views.
    Includes all related data and computed fields for full context.
    
    PERFORMANCE CONSIDERATION: Only used for detail views, not lists,
    to avoid N+1 queries and oversized responses.
    """
    
    # Nested serializers for related objects
    user = UserBasicSerializer(read_only=True)
    movie = MovieBasicSerializer(read_only=True)
    
    # Computed fields for better UX
    metadata_dict = serializers.SerializerMethodField()
    action_type_display = serializers.CharField(
        source='get_action_type_display', 
        read_only=True,
        help_text="Human-readable action type"
    )
    
    class Meta:
        model = UserActivityLog
        fields = [
            'id', 'user', 'session_id', 'action_type', 'action_type_display',
            'movie', 'ip_address', 'user_agent', 'referer', 'source',
            'metadata_dict', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']

    def get_metadata_dict(self, obj):
        """
        Convert metadata JSON string back to dict for API response.
        
        WHY SERIALIZERMETHODFIELD: Allows custom logic and handles
        JSON parsing errors gracefully.
        """
        return obj.get_metadata_dict()


class UserActivityLogListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    
    PERFORMANCE OPTIMIZATION: Excludes heavy fields like user_agent (can be very long)
    and includes only essential data to keep list responses fast and lean.
    
    NAMING STRATEGY: Using source paths like 'user.username' to avoid additional
    database queries while still showing useful information.
    """
    
    # Flattened fields to avoid nested objects in lists
    user_username = serializers.CharField(source='user.username', read_only=True)
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = UserActivityLog
        fields = [
            'id', 'user_username', 'action_type', 'action_type_display',
            'movie_title', 'source', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class PopularityMetricsSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for popularity metrics.
    
    DESIGN DECISION: Read-only because these metrics are computed automatically
    by background tasks, not user input. Including computed engagement score
    for frontend convenience.
    """
    movie = MovieBasicSerializer(read_only=True)
    engagement_score = serializers.ReadOnlyField()  # Computed property from model
    
    class Meta:
        model = PopularityMetrics
        fields = [
            'id', 'movie', 'date', 'view_count', 'like_count',
            'rating_count', 'average_rating', 'recommendation_count',
            'click_through_rate', 'engagement_score'
        ]
        read_only_fields = ['id', 'date']  # Date is auto-set


class TrendingMoviesSerializer(serializers.Serializer):
    """
    Serializer for trending movies aggregated data.
    
    WHY PLAIN SERIALIZER: This handles output from database aggregation queries
    (like PopularityMetrics.get_trending_movies()), not model instances.
    
    NAMING: Field names match the aggregation aliases from the model method.
    """
    movie_id = serializers.IntegerField()
    movie_title = serializers.CharField(read_only=True)
    total_views = serializers.IntegerField()
    total_likes = serializers.IntegerField()
    avg_ctr = serializers.DecimalField(max_digits=5, decimal_places=2)
    avg_rating = serializers.FloatField(allow_null=True)  # Might be null if no ratings
    
    def to_representation(self, instance):
        """
        Custom representation to enrich data with movie details.
        
        WHY OVERRIDE: The aggregation query only returns movie IDs,
        but we want to include movie titles for frontend convenience.
        """
        data = super().to_representation(instance)
        
        # If movie info not included in aggregation, fetch it
        if 'movie_title' not in instance or not instance['movie_title']:
            try:
                from movies.models import Movie  # Local import to avoid circular deps
                movie = Movie.objects.get(id=instance['movie'])
                data['movie_title'] = movie.title
            except:
                data['movie_title'] = 'Unknown Movie'
        
        return data


class ActivityAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for activity analytics data.
    
    USE CASE: Dashboard endpoints that return aggregated statistics
    like "Movie views: 150 (45%)", "Ratings: 75 (23%)", etc.
    
    WHY PLAIN SERIALIZER: This represents computed analytics, not model data.
    """
    action_type = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()
    display_name = serializers.CharField(required=False)  # Human-readable name


class UserActivitySummarySerializer(serializers.Serializer):
    """
    Serializer for user activity summary.
    
    PURPOSE: Provides aggregate data for user profiles or dashboards.
    Shows a user's activity patterns and engagement level.
    
    DESIGN: Combines user info with computed statistics.
    """
    user = UserBasicSerializer()
    total_activities = serializers.IntegerField()
    movie_views = serializers.IntegerField()
    ratings_given = serializers.IntegerField()
    favorites_added = serializers.IntegerField()
    watchlist_additions = serializers.IntegerField()
    last_activity = serializers.DateTimeField()
    most_active_day = serializers.DateField(allow_null=True)
    engagement_level = serializers.CharField()  # 'low', 'medium', 'high'


class BulkActivityLogSerializer(serializers.Serializer):
    """
    Serializer for bulk activity logging.
    
    USE CASE: Mobile apps or batch processing that need to log multiple
    activities at once for performance reasons.
    
    WHY SEPARATE SERIALIZER: Bulk operations have different validation
    and processing requirements than single creates.
    """
    activities = UserActivityLogCreateSerializer(many=True)
    
    def validate_activities(self, value):
        """
        Custom validation for bulk activities.
        
        BUSINESS RULES:
        1. Limit bulk size to prevent abuse
        2. Ensure at least one activity
        3. Validate unique session constraints if needed
        """
        if not value:
            raise serializers.ValidationError("At least one activity is required.")
        
        if len(value) > 100:  # Reasonable limit
            raise serializers.ValidationError("Maximum 100 activities per bulk request.")
        
        return value
    
    def create(self, validated_data):
        """
        Bulk create activities for better performance.
        
        OPTIMIZATION: Uses bulk_create instead of individual saves
        for better database performance with large batches.
        """
        activities_data = validated_data['activities']
        activities = []
        
        for activity_data in activities_data:
            metadata_dict = activity_data.pop('metadata_dict', None)
            activity = UserActivityLog(**activity_data)
            
            if metadata_dict:
                activity.set_metadata_dict(metadata_dict)
            
            activities.append(activity)
        
        # Bulk create for performance
        created_activities = UserActivityLog.objects.bulk_create(activities)
        return {'created_count': len(created_activities), 'activities': created_activities}


class SessionAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for session-based analytics.
    
    PURPOSE: Track user behavior patterns within sessions.
    Useful for understanding user journeys and conversion funnels.
    """
    session_id = serializers.CharField()
    user = UserBasicSerializer(allow_null=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    duration_minutes = serializers.FloatField()
    activity_count = serializers.IntegerField()
    unique_movies_viewed = serializers.IntegerField()
    conversion_events = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of conversion actions like 'rating_submit', 'favorite_add'"
    )