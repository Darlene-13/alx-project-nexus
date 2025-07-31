# recommendations/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q, F
from datetime import timedelta

User = get_user_model()

class UserMovieInteraction(models.Model):
    """
    This app tracks the user interactions with movies for analytics and recommendation purposes.
    It includes the user activity logs, movie ratings, and daily metrics for the movies.
    """

    INTERACTION_TYPES = [
        ('view', 'View'),
        ('like', 'Like'),
        ('dislike', 'Dislike'),
        ('click', 'Click'),
        ('rating', 'Rating'),
        ('favorite', 'Favorite'),
        ('watchlist', 'Watchlist'),
    ]
    FEEDBACK_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    SOURCE_CHOICES = [
        ('web', 'Web'),
        ('mobile', 'Mobile App'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_interactions')
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=50, choices=INTERACTION_TYPES, null=True, blank=True)
    rating = models.FloatField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Integrated feedback settings
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_CHOICES, null=True, blank=True)
    feedback_comment = models.TextField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, null=True, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'user_movie_interactions'
        verbose_name = 'User Movie Interaction'
        verbose_name_plural = 'User Movie Interactions'
        ordering = ['-timestamp']
        constraints = [
            models.UniqueConstraint(fields=['user', 'movie', 'interaction_type'], name='unique_user_movie_interaction')
        ]
        indexes = [
            models.Index(fields=['user', 'interaction_type'], name='idx_interactions_user_type'),
            models.Index(fields=['movie', 'interaction_type'], name='idx_interactions_movie_type'),
            models.Index(fields=['timestamp'], name='idx_interactions_timestamp'),
            models.Index(fields=['rating'], name='idx_interactions_rating'),
            models.Index(fields=['feedback_type'], name='idx_interactions_feedback'),
        ]

    def __str__(self):
        user_info = self.user.username if self.user else 'Anonymous'
        movie_info = self.movie.title if self.movie else 'N/A'
        return f"UserMovieInteraction(id={self.id}, user={user_info}, movie={movie_info}, interaction_type={self.interaction_type}, timestamp={self.timestamp})"

    
    @property
    def is_recent(self):
        """Check if interaction happened within last 24 hours"""
        return self.timestamp >= timezone.now() - timedelta(hours=24)
    
    @property
    def is_positive_feedback(self):
        """Check if interaction indicates positive user sentiment"""
        positive_types = ['like', 'favorite', 'watchlist']
        positive_feedback = self.feedback_type == 'positive'
        high_rating = self.rating and self.rating >= 4.0
        
        return (self.interaction_type in positive_types or 
                positive_feedback or high_rating)
    
    @property
    def engagement_weight(self):
        """Calculate engagement weight for recommendation algorithms"""
        weights = {
            'view': 1.0,
            'like': 3.0,
            'dislike': -2.0,
            'click': 1.5,
            'rating': 2.0,
            'favorite': 5.0,
            'watchlist': 4.0,
        }
        base_weight = weights.get(self.interaction_type, 1.0)
        
        # Boost for high ratings
        if self.rating and self.rating >= 4.0:
            base_weight *= 1.5
        elif self.rating and self.rating <= 2.0:
            base_weight *= 0.5
            
        return base_weight
    
    @classmethod
    def create_interaction(cls, user, movie, interaction_type, source='web', **kwargs):
        """Convenient method to create interactions with validation"""
        return cls.objects.create(
            user=user,
            movie=movie,
            interaction_type=interaction_type,
            source=source,
            **kwargs
        )
    
    @classmethod
    def get_movie_average_rating(cls, movie):
        """Calculate average rating for a specific movie"""
        avg_rating = cls.objects.filter(
            movie=movie,
            interaction_type='rating',
            rating__isnull=False
        ).aggregate(avg_rating=Avg('rating'))['avg_rating']
        
        return round(avg_rating, 2) if avg_rating else None
    
    @classmethod
    def get_user_preferred_genres(cls, user, limit=5):
        """Get user's most interacted genres for recommendations"""
        from django.db.models import Count
        
        # Get genres from movies user interacted with positively
        interactions = cls.objects.filter(
            user=user,
            interaction_type__in=['like', 'favorite', 'watchlist']
        ).select_related('movie')
        
        genre_counts = {}
        for interaction in interactions:
            if hasattr(interaction.movie, 'genres'):
                for genre in interaction.movie.genres.all():
                    genre_counts[genre] = genre_counts.get(genre, 0) + interaction.engagement_weight
        
        # Sort by engagement weight
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
        return [genre for genre, weight in sorted_genres[:limit]]
    
    @classmethod
    def get_similar_users(cls, user, min_common_movies=3):
        """Find users with similar movie preferences"""
        user_movies = set(cls.objects.filter(
            user=user,
            interaction_type__in=['like', 'favorite', 'rating']
        ).values_list('movie_id', flat=True))
        
        if not user_movies:
            return cls.objects.none()
        
        # Find users who interacted with same movies
        similar_users = cls.objects.filter(
            movie_id__in=user_movies,
            interaction_type__in=['like', 'favorite', 'rating']
        ).exclude(user=user).values('user').annotate(
            common_movies=Count('movie_id', distinct=True)
        ).filter(common_movies__gte=min_common_movies).order_by('-common_movies')
        
        return [item['user'] for item in similar_users]
    
    @classmethod
    def get_trending_movies(cls, days=7, interaction_types=None):
        """Get trending movies based on recent interactions"""
        if interaction_types is None:
            interaction_types = ['view', 'like', 'favorite']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            timestamp__gte=cutoff_date,
            interaction_type__in=interaction_types
        ).values('movie').annotate(
            interaction_count=Count('id'),
            unique_users=Count('user', distinct=True)
        ).order_by('-interaction_count', '-unique_users')
    
    def update_feedback(self, feedback_type, comment=None):
        """Update feedback for this interaction"""
        self.feedback_type = feedback_type
        if comment:
            self.feedback_comment = comment
        self.save(update_fields=['feedback_type', 'feedback_comment'])
    
    def to_recommendation_data(self):
        """Convert interaction to data useful for recommendation algorithms"""
        return {
            'user_id': self.user.id,
            'movie_id': self.movie.id,
            'interaction_type': self.interaction_type,
            'rating': self.rating,
            'engagement_weight': self.engagement_weight,
            'timestamp': self.timestamp,
            'is_positive': self.is_positive_feedback
        }


class UserRecommendations(models.Model):
    """
    This is the user recommendations model that stores personalized movie recommendations for each user.
    It includes the recommended movies, their scores and their sources.
    """
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='recommendations')
    score = models.FloatField(default=0.00, help_text="Recommendation score for the movie")
    algorithm = models.CharField(max_length=50)
    
    # Timestamp
    generated_at = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_recommendations'
        verbose_name = 'User Recommendation'
        verbose_name_plural = 'User Recommendations'
        ordering = ['-score', '-generated_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'movie', 'algorithm'], name='unique_user_movie_algorithm')
        ]
        indexes = [
            models.Index(fields=['user', 'score'], name='idx_recommendations_user_score'),
            models.Index(fields=['generated_at'], name='idx_recommendations_generated'),
            models.Index(fields=['algorithm'], name='idx_recommendations_algorithm'),
            models.Index(fields=['clicked', 'clicked_at'], name='idx_recommendations_clicked')
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.movie.title} ({self.algorithm}: {self.score})"
    
    @property
    def is_fresh(self):
        """Check if recommendation is still fresh (within 7 days)"""
        return self.generated_at >= timezone.now() - timedelta(days=7)
    
    @property
    def click_through_time(self):
        """Time between generation and click (if clicked)"""
        if self.clicked and self.clicked_at:
            return self.clicked_at - self.generated_at
        return None
    
    @property
    def relevance_score(self):
        """Calculate relevance based on score and freshness"""
        base_score = self.score
        
        # Reduce score for older recommendations
        days_old = (timezone.now() - self.generated_at).days
        freshness_factor = max(0.1, 1.0 - (days_old * 0.1))
        
        return round(base_score * freshness_factor, 2)
    
    @classmethod
    def generate_for_user(cls, user, algorithm='collaborative_filtering', limit=10):
        """Generate recommendations for a single user"""
        # Get user's preferences from interactions
        user_interactions = UserMovieInteraction.objects.filter(user=user)
        
        if not user_interactions.exists():
            # New user - recommend popular movies
            return cls._recommend_popular_movies(user, algorithm, limit)
        
        # Get user's preferred genres
        preferred_genres = UserMovieInteraction.get_user_preferred_genres(user)
        
        # Get movies user hasn't interacted with
        interacted_movies = user_interactions.values_list('movie_id', flat=True)
        
        # Simple genre-based recommendation (you can enhance this)
        from movies.models import Movie  # Adjust import as needed
        candidate_movies = Movie.objects.exclude(
            id__in=interacted_movies
        ).filter(
            genres__in=preferred_genres
        ).distinct()[:limit * 2]  # Get more candidates
        
        recommendations = []
        for movie in candidate_movies[:limit]:
            score = cls._calculate_recommendation_score(user, movie, algorithm)
            
            recommendation = cls.objects.create(
                user=user,
                movie=movie,
                score=score,
                algorithm=algorithm
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    @classmethod
    def generate_for_all_users(cls, algorithm='collaborative_filtering', batch_size=100):
        """Generate recommendations for all active users"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get active users (you might want to filter further)
        active_users = User.objects.filter(is_active=True)
        
        total_generated = 0
        for user in active_users:
            try:
                recommendations = cls.generate_for_user(user, algorithm)
                total_generated += len(recommendations)
                
                # Process in batches to avoid memory issues
                if total_generated % batch_size == 0:
                    print(f"Generated {total_generated} recommendations...")
                    
            except Exception as e:
                print(f"Error generating recommendations for user {user.id}: {e}")
                continue
        
        return total_generated
    
    @classmethod
    def get_user_recommendations(cls, user, limit=10, algorithm=None):
        """Get fresh recommendations for a user"""
        queryset = cls.objects.filter(user=user)
        
        if algorithm:
            queryset = queryset.filter(algorithm=algorithm)
        
        # Prefer fresh, unclicked, high-scoring recommendations
        return queryset.filter(
            generated_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-score', 'clicked', '-generated_at')[:limit]
    
    @classmethod
    def send_batch_notifications(cls, algorithm=None, limit_per_user=5):
        """Send recommendation notifications to users"""
        # Get users with fresh recommendations
        recent_cutoff = timezone.now() - timedelta(hours=24)
        
        queryset = cls.objects.filter(
            generated_at__gte=recent_cutoff,
            clicked=False
        )
        
        if algorithm:
            queryset = queryset.filter(algorithm=algorithm)
        
        # Group by user
        users_with_recs = queryset.values('user').distinct()
        
        notifications_sent = 0
        for user_data in users_with_recs:
            user_id = user_data['user']
            user_recs = queryset.filter(user_id=user_id).order_by('-score')[:limit_per_user]
            
            try:
                # This would integrate with your notification service
                success = cls._send_user_notification(user_id, list(user_recs))
                if success:
                    notifications_sent += 1
            except Exception as e:
                print(f"Failed to send notification to user {user_id}: {e}")
        
        return notifications_sent
    
    @classmethod
    def get_algorithm_performance(cls, algorithm, days=30):
        """Analyze performance of a recommendation algorithm"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        recs = cls.objects.filter(
            algorithm=algorithm,
            generated_at__gte=cutoff_date
        )
        
        total_recs = recs.count()
        clicked_recs = recs.filter(clicked=True).count()
        avg_score = recs.aggregate(avg_score=Avg('score'))['avg_score']
        
        return {
            'algorithm': algorithm,
            'total_recommendations': total_recs,
            'clicked_recommendations': clicked_recs,
            'click_through_rate': round(clicked_recs / total_recs * 100, 2) if total_recs > 0 else 0,
            'average_score': round(avg_score, 2) if avg_score else 0,
            'period_days': days
        }
    
    @classmethod
    def cleanup_old_recommendations(cls, days=30):
        """Remove old, unclicked recommendations to keep database clean"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_recs = cls.objects.filter(
            generated_at__lt=cutoff_date,
            clicked=False
        )
        
        count = old_recs.count()
        old_recs.delete()
        
        return count
    
    def mark_as_clicked(self):
        """Mark this recommendation as clicked"""
        self.clicked = True
        self.clicked_at = timezone.now()
        self.save(update_fields=['clicked', 'clicked_at'])
        
        # Optionally log this as an interaction
        UserMovieInteraction.create_interaction(
            user=self.user,
            movie=self.movie,
            interaction_type='recommendation_click',
            metadata={'recommendation_id': self.id, 'algorithm': self.algorithm}
        )
    
    def update_score(self, new_score):
        """Update recommendation score"""
        self.score = new_score
        self.save(update_fields=['score'])
    
    def to_api_format(self):
        """Convert to format suitable for API responses"""
        return {
            'id': self.id,
            'movie_id': self.movie.id,
            'movie_title': self.movie.title,
            'score': self.score,
            'algorithm': self.algorithm,
            'generated_at': self.generated_at.isoformat(),
            'is_fresh': self.is_fresh,
            'relevance_score': self.relevance_score
        }

    # === PRIVATE HELPER METHODS ===
    
    @classmethod
    def _recommend_popular_movies(cls, user, algorithm, limit):
        """Fallback recommendations for new users"""
        from movies.models import Movie
        
        # Get popular movies from recent interactions
        popular_movie_ids = UserMovieInteraction.get_trending_movies(days=30)[:limit]
        
        recommendations = []
        for movie_data in popular_movie_ids:
            movie = Movie.objects.get(id=movie_data['movie'])
            score = movie_data['interaction_count'] / 100.0  # Normalize score
            
            recommendation = cls.objects.create(
                user=user,
                movie=movie,
                score=min(score, 10.0),  # Cap at 10
                algorithm=f"{algorithm}_popular"
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    @classmethod
    def _calculate_recommendation_score(cls, user, movie, algorithm):
        """Calculate recommendation score based on algorithm"""
        # Simple scoring 
        base_score = 5.0
        
        # Boost for user's preferred genres
        user_genres = UserMovieInteraction.get_user_preferred_genres(user)
        if hasattr(movie, 'genres'):
            common_genres = set(movie.genres.all()) & set(user_genres)
            base_score += len(common_genres) * 0.5
        
        # Boost for movie popularity
        avg_rating = UserMovieInteraction.get_movie_average_rating(movie)
        if avg_rating:
            base_score += (avg_rating - 3.0)  # Boost for above-average movies
        
        return round(min(base_score, 10.0), 2)
    
    @classmethod
    def _send_user_notification(cls, user_id, recommendations):
        """Send notification to user about new recommendations"""
        # This would integrate with your notification service (email, push, etc.)
        # For now, just print (replace with actual notification logic)
        
        try:
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            print(f"Sending notification to {user.username}")
            print(f"Recommendations: {len(recommendations)} movies")
            
            # Here you would call your notification service:
            # - Email service
            # - Push notification service  
            # - SMS service
            # - In-app notification
            
            return True
        except Exception as e:
            print(f"Notification failed: {e}")
            return False