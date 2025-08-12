
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
        
        Respects AUTO_UPDATE_METRICS setting to prevent overriding seeded data
        """
        from django.conf import settings
        
        # Check if auto-updates are disabled (useful during development/testing)
        if not getattr(settings, 'AUTO_UPDATE_METRICS', True):
            print(f"⚠️  Skipping metric update for {movie.title} - AUTO_UPDATE_METRICS is disabled")
            return None
        
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
        
        # If metric already exists and auto-update is enabled, recalculate
        # If created new, always calculate
        if created or getattr(settings, 'FORCE_METRIC_RECALCULATION', False):
            print(f"📊 {'Creating' if created else 'Updating'} metrics for {movie.title} on {date}")
            
            # Calculate metrics from activity logs for this day
            from django.db.models import Count, Avg
            
            activities = UserActivityLog.objects.filter(
                movie=movie,
                timestamp__date=date
            )
            
            # Store original values for comparison
            original_views = metric.view_count
            
            # Update view count
            metric.view_count = activities.filter(action_type='movie_view').count()
            
            # Update like count (from favorite_add actions)
            metric.like_count = activities.filter(action_type='favorite_add').count()
            
            # Update rating metrics
            ratings = activities.filter(action_type='rating_submit')
            metric.rating_count = ratings.count()
            
            # Calculate average rating from metadata
            if metric.rating_count > 0:
                rating_values = []
                for rating_activity in ratings:
                    try:
                        metadata = json.loads(rating_activity.metadata) if rating_activity.metadata else {}
                        rating_value = metadata.get('rating_value')
                        if rating_value:
                            rating_values.append(float(rating_value))
                    except (json.JSONDecodeError, ValueError, TypeError):
                        pass
                
                if rating_values:
                    metric.average_rating = round(sum(rating_values) / len(rating_values), 1)
                else:
                    metric.average_rating = 0.0
            else:
                metric.average_rating = 0.0
            
            # Update recommendation metrics
            recommendations = activities.filter(action_type='recommendation_click')
            metric.recommendation_count = recommendations.count()
            
            # Calculate CTR (recommendations clicked / recommendations shown)
            # For now, use a simplified calculation
            if metric.view_count > 0:
                metric.click_through_rate = round(
                    (metric.recommendation_count / metric.view_count) * 100, 2
                )
            else:
                metric.click_through_rate = 0.00
            
            # Log significant changes for debugging
            if not created and original_views != metric.view_count:
                print(f"📈 Views changed for {movie.title}: {original_views} → {metric.view_count}")
            
            metric.save()
            
            print(f"✅ Updated metrics for {movie.title}: {metric.view_count} views, {metric.like_count} likes, {metric.rating_count} ratings")
            
        else:
            print(f"📊 Skipping update for {movie.title} on {date} - metric exists and auto-update enabled")
        
        return metric

    # Enhanced version with force update option
    @classmethod
    def force_update_daily_metrics(cls, movie, date=None):
        """
        Force update metrics regardless of AUTO_UPDATE_METRICS setting.
        Useful for admin actions or manual updates.
        """
        from django.conf import settings
        
        # Temporarily override the setting
        original_setting = getattr(settings, 'AUTO_UPDATE_METRICS', True)
        original_force = getattr(settings, 'FORCE_METRIC_RECALCULATION', False)
        
        # Force the update
        settings.AUTO_UPDATE_METRICS = True
        settings.FORCE_METRIC_RECALCULATION = True
        
        try:
            result = cls.update_daily_metrics(movie, date)
            print(f"🔄 Force updated metrics for {movie.title}")
            return result
        finally:
            # Restore original settings
            settings.AUTO_UPDATE_METRICS = original_setting
            settings.FORCE_METRIC_RECALCULATION = original_force

    # Batch update method for admin actions
    @classmethod
    def batch_update_metrics(cls, movies=None, date=None, force=False):
        """
        Update metrics for multiple movies.
        
        Args:
            movies: QuerySet of movies to update (default: all movies)
            date: Date to update metrics for (default: today)
            force: Whether to force update regardless of settings
        """
        from apps.movies.models import Movie
        
        if movies is None:
            movies = Movie.objects.all()
        
        if date is None:
            date = timezone.now().date()
        
        updated_count = 0
        skipped_count = 0
        
        print(f"📊 Batch updating metrics for {movies.count()} movies on {date}")
        
        for movie in movies:
            if force:
                result = cls.force_update_daily_metrics(movie, date)
            else:
                result = cls.update_daily_metrics(movie, date)
            
            if result:
                updated_count += 1
            else:
                skipped_count += 1
            
            # Progress indicator for large batches
            if (updated_count + skipped_count) % 10 == 0:
                print(f"   → Processed {updated_count + skipped_count} movies...")
        
        print(f"✅ Batch update complete: {updated_count} updated, {skipped_count} skipped")
        return updated_count, skipped_count

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
