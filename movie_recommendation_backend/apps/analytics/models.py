
from multiprocessing.dummy import Manager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Sum, Avg

User = get_user_model()
class UserActivityLog(models.Model):
    """
    This model defines all the user activity logs for analytics and machine learning purposes.
    It tracks both authenticaed and anonymous user activities.
    """
    ACTION_TYPES = [
                ('movie_view', 'Movie View'),
                ('movie_search', 'Movie Search'),
                ('recommendation_click', 'Recommendation Click'),
                ('email_open', 'Email Open'),
                ('email_click', 'Email Click'),
                ('push_click', 'Push Click'),
                ('rating_submit', 'Rating Submit'),
                ('favorite_add', 'Favorite Add'),
                ('watchlist_add', 'Watchlist Add'),
            ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    session_id = models.CharField(max_length=255, null=True, blank=True)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES, null=True, blank=True)
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='activity_logs', null=True, blank=True)
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # IP address of the user
    user_agent = models.TextField(null=True, blank=True)  # User agent string
    referer = models.CharField(max_length=255, null=True, blank=True, help_text="HTTP header")  # Referring URL
    source = models.CharField(max_length=50, null=True, blank=True)  # Source of the action (e.g., web, mobile app)
    metadata = models.JSONField(null=True, blank=True)  # Additional metadata about the action
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)  # When the action was performed

    class Meta:
        db_table = 'user_activity_logs'
        verbose_name = 'User Activity Log'
        verbose_name_plural = 'User Activity Logs'
        ordering = ['-timestamp']  # Order by timestamp descending

        indexes = [
            models.Index(fields=['user', 'action_type'], name = 'idx_activity_logs_user_action'),
            models.Index(fields=['movie_id', 'action_type'], name='idx_activity_logs_movie_action'),
            models.Index(fields=['timestamp'], name='idx_activity_logs_timestamp'),
            models.Index(fields=['session_id'], name='idx_activity_logs_session'),
            models.Index(fields=['source'], name='idx_activity_logs_source'),
        ]

    def __str__(self):
        user_info = self.user.username if self.user else 'Anonymous'
        movie_info = self.movie.title if self.movie else 'N/A'
        return f"UserActivityLog(id={self.id}, user={user_info}, action_type={self.action_type}, movie={movie_info}, timestamp={self.timestamp})"
    
    def get_metadata_dict(self):
        """ 
        Returns the metadata as dictionary in JSON format.
        """
        try:
            return json.loads(self.metadata)
        except (TypeError, json.JSONDecodeError):
            return {
                "error": "Invalid metadata format"
            }
        
    def set_metadata_dict(self, metadata_dict):
        """
        Sets the metadata from a dictionary.
        """
        try:
            self.metadata = json.dumps(metadata_dict)
        except (TypeError, ValueError):
            raise ValueError("Invalid metadata format. Must be a dictionary.")

        self.metadata = json.dumps(metadata_dict)

    @classmethod
    def log_activity(cls, action_type, session_id, ip_address, user_agent, source, user=None, movie=None, referer=None, metadata=None):
        """
        This one logs user activity to the database.
        """
        return cls.objects.create(
            user=user,
            session_id=session_id,
            action_type=action_type,
            movie=movie,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            source=source,
            metadata=json.dumps(metadata) if metadata else None
        )

class PopularityMetrics(models.Model):
    """
    This model defines the popularity metrics for the movies based on the user activity logs.
    They are aggregated on a daily basis.
    """
    id = models.BigAutoField(primary_key=True)
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='popularity_metrics')

    # Date for the metrics
    date = models.DateField(auto_now_add=True, help_text="Date for the metrics")
    # Daily aggregated metrics
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    recommendation_count = models.PositiveIntegerField(default=0)
    click_through_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)


    class Meta:
        db_table = 'popularity_metrics'
        verbose_name = 'Popularity Metric'
        verbose_name_plural = 'Popularity Metrics'
        ordering = ['-date', '-movie']  # Order by date descending, then by movie
        constraints = [
            models.UniqueConstraint(fields=['movie_id', 'date'], name='unique_popularity_metrics_per_movie_per_day')
        ]
        indexes = [
                models.Index(fields=['movie'], name='idx_popularity_movie'),
                models.Index(fields=['view_count'], name='idx_popularity_views'),
                models.Index(fields=['date'], name='idx_popularity_date'),
                models.Index(fields=['click_through_rate'], name='idx_popularity_ctr'),        
        ]
    def __str__ (self):
        return f"PopularityMetrics(movie={self.movie.title}, date={self.date}, view_count={self.view_count}, like_count={self.like_count}, rating_count={self.rating_count}, average_rating={self.average_rating}, recommendation_count={self.recommendation_count}, click_through_rate={self.click_through_rate})"
    
    @property
    def engagement_score(self):
        """
        Calculates a composite engagement score based on view count, like count, and rating count.
        """
        score = 0
        score += self.view_count * 1
        score += self.like_count * 2
        score += self.rating_count * 3
        score += self.recommendation_count * 1.5
        score += float(self.click_through_rate) * 100  # Assuming click-through rate is a percentage
        if self.average_rating:
            score += self.average_rating * 10
        return round(score, 2)
    
    @classmethod
    def get_trending_movies(cls, days=7, limit=10):
        """
        Returns the top trending movies based on their engagement scores.
        """
        cutoff_date = timezone.now().date() - timezone.timedelta(days=days)

        return cls.objects.filter(
            date__gte=cutoff_date
        ).values('movie').annotate(
            total_views=Sum('view_count'),
            total_likes=Sum('like_count'),
            avg_ctr=Avg('click_through_rate'),
            average_rating=Avg('average_rating')
        ).order_by('-total_views')[:limit]
    
    @classmethod
    def update_daily_metrics(cls, movie, date=None):
        """
        Update or create daily metrics for a movie
        Called by background tasks or signals
        """
        if date is None:
            date = timezone.now().date()
        
        # Get or create the metric record
        metric, created = cls.objects.get_or_create(
            movie=movie,
            date=date,
            defaults={
                'view_count': 0,
                'like_count': 0,
                'rating_count': 0,
                'recommendation_count': 0,
                'click_through_rate': 0.0000
            }
        )
        
        # Calculate metrics from activity logs for this day
        from django.db.models import Count, Avg
        
        activities = UserActivityLog.objects.filter(
            movie=movie,
            timestamp__date=date
        )
        
        # Update view count
        metric.view_count = activities.filter(action_type='movie_view').count()
        
        # Update rating metrics
        ratings = activities.filter(action_type='rating_submit')
        metric.rating_count = ratings.count()
        
        # Update recommendation metrics
        recommendations = activities.filter(action_type='recommendation_click')
        metric.recommendation_count = recommendations.count()
        
        # Calculate CTR (recommendations clicked / recommendations shown)
        # This would need additional tracking of recommendation impressions
        
        metric.save()
        return metric

#Manager for common queries
class UserActivityLogManager(models.Manager):
    def for_user(self, user):
        """Get activities for a specific user"""
        return self.filter(user=user)
    
    def for_session(self, session_id):
        """Get activities for a specific session"""
        return self.filter(session_id=session_id)
    
    def by_action(self, action_type):
        """Filter by action type"""
        return self.filter(action_type=action_type)
    
    def recent(self, hours=24):
        """Get recent activities within specified hours"""
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(timestamp__gte=cutoff)


# Add custom manager to UserActivityLog
UserActivityLog.add_to_class('objects', UserActivityLogManager())
