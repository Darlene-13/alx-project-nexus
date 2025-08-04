"""
AI-Powered Recommendation Service

This service implements collaborative filtering, content-based filtering,
and hybrid recommendation algorithms for personalized movie recommendations.

Features:
- Collaborative Filtering (User-Based & Item-Based)
- Content-Based Filtering (Genre, Cast, Director similarity)
- Hybrid Algorithm combining multiple approaches
- Real-time Learning from user interactions
- Performance optimizations with caching

"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json
import math

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, Avg, Count, F
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.movies.models import Movie
from apps.recommendations.models import (
     UserMovieInteraction,UserRecommendations
 )
from apps.authentication.models import User  

User = get_user_model()
logger = logging.getLogger(__name__)

# RECOMMENDATION ALGORITHMS IMPLEMENTATION

class RecommendationService:
    """
    AI-Powered Movie Recommendation Service
    
    Implements multiple recommendation algorithms:
    1. Collaborative Filtering (User-Based & Item-Based)
    2. Content-Based Filtering 
    3. Popularity-Based Recommendations
    4. Hybrid Algorithm
    5. Real-time Learning
    """
    
    def __init__(self):
        """Initialize the recommendation service."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Algorithm weights for hybrid recommendations
        self.algorithm_weights = {
            'collaborative': 0.4,
            'content_based': 0.3,
            'popularity': 0.2,
            'trending': 0.1
        }
        
        # Similarity thresholds
        self.min_similarity_threshold = 0.1
        self.min_common_items = 3  # Minimum common ratings for user similarity
        
        # Cache timeouts (seconds)
        self.cache_timeouts = {
            'user_recommendations': 3600,    # 1 hour
            'similar_movies': 86400,         # 24 hours
            'user_similarity': 7200,         # 2 hours
            'movie_features': 86400,         # 24 hours
            'popular_movies': 1800           # 30 minutes
        }
        
        self.logger.info("Recommendation service initialized")
    
    # COLLABORATIVE FILTERING ALGORITHMS
    
    def get_user_based_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        User-based collaborative filtering.
        Find users with similar tastes and recommend their highly-rated movies.
        
        Args:
            user_id: Target user ID
            limit: Number of recommendations to return
            
        Returns:
            List of recommended movies with scores
        """
        cache_key = f'user_collab_recs_{user_id}_{limit}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        self.logger.info(f"Computing user-based recommendations for user {user_id}")
        
        try:
            # Get user's ratings (you'll need to adjust based on your actual models)
            user_ratings = self._get_user_ratings(user_id)
            if not user_ratings:
                return self._get_popular_movies_as_recommendations(limit)
            
            # Find similar users
            similar_users = self._find_similar_users(user_id, user_ratings)
            if not similar_users:
                return self._get_popular_movies_as_recommendations(limit)
            
            # Get recommendations from similar users
            recommendations = self._get_recommendations_from_similar_users(
                user_id, similar_users, limit
            )
            
            # Cache the results
            cache.set(cache_key, recommendations, self.cache_timeouts['user_recommendations'])
            
            self.logger.info(f"Generated {len(recommendations)} user-based recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error in user-based recommendations for user {user_id}: {e}")
            return self._get_popular_movies_as_recommendations(limit)
    
    def get_item_based_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Item-based collaborative filtering.
        Find movies similar to ones the user has rated highly.
        
        Args:
            user_id: Target user ID
            limit: Number of recommendations to return
            
        Returns:
            List of recommended movies with scores
        """
        cache_key = f'item_collab_recs_{user_id}_{limit}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        self.logger.info(f"Computing item-based recommendations for user {user_id}")
        
        try:
            # Get user's highly rated movies
            user_high_rated = self._get_user_high_rated_movies(user_id, min_rating=4.0)
            if not user_high_rated:
                return self._get_popular_movies_as_recommendations(limit)
            
            # Find movies similar to user's favorites
            recommendations = []
            seen_movies = set(self._get_user_watched_movies(user_id))
            
            for movie_id, rating in user_high_rated.items():
                similar_movies = self._find_similar_movies(movie_id, limit=20)
                
                for similar_movie in similar_movies:
                    similar_movie_id = similar_movie['movie_id']
                    similarity_score = similar_movie['similarity']
                    
                    if similar_movie_id not in seen_movies:
                        # Weight similarity by user's rating of the source movie
                        weighted_score = similarity_score * (rating / 5.0)
                        
                        recommendations.append({
                            'movie_id': similar_movie_id,
                            'score': weighted_score,
                            'algorithm': 'item_collaborative',
                            'source_movie_id': movie_id
                        })
            
            # Aggregate scores for movies recommended multiple times
            recommendations = self._aggregate_recommendations(recommendations)
            recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:limit]
            
            # Add movie details
            recommendations = self._enrich_recommendations_with_movie_data(recommendations)
            
            # Cache the results
            cache.set(cache_key, recommendations, self.cache_timeouts['user_recommendations'])
            
            self.logger.info(f"Generated {len(recommendations)} item-based recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error in item-based recommendations for user {user_id}: {e}")
            return self._get_popular_movies_as_recommendations(limit)

    # CONTENT-BASED FILTERING
    
    def get_content_based_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Content-based filtering recommendations.
        Recommend movies similar to user's preferences based on content features.
        
        Args:
            user_id: Target user ID
            limit: Number of recommendations to return
            
        Returns:
            List of recommended movies with scores
        """
        cache_key = f'content_recs_{user_id}_{limit}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        self.logger.info(f"Computing content-based recommendations for user {user_id}")
        
        try:
            # Get user's content preferences
            user_profile = self._build_user_content_profile(user_id)
            if not user_profile:
                return self._get_popular_movies_as_recommendations(limit)
            
            # Get candidate movies (unwatched by user)
            watched_movies = set(self._get_user_watched_movies(user_id))
            candidate_movies = Movie.objects.filter(
                ~Q(id__in=watched_movies),
                tmdb_rating__gte=6.0  # Filter out very low-rated movies
            ).order_by('-popularity_score')[:1000]  # Limit for performance
            
            # Score each candidate movie
            recommendations = []
            
            for movie in candidate_movies:
                content_score = self._calculate_content_similarity(user_profile, movie)
                
                if content_score > self.min_similarity_threshold:
                    recommendations.append({
                        'movie_id': movie.id,
                        'score': content_score,
                        'algorithm': 'content_based',
                        'movie_data': {
                            'title': movie.title,
                            'year': movie.year,
                            'genres': movie.genre_names,
                            'tmdb_rating': float(movie.tmdb_rating) if movie.tmdb_rating else None,
                            'poster_url': movie.poster_url
                        }
                    })
            
            # Sort by score and limit results
            recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:limit]
            
            # Cache the results
            cache.set(cache_key, recommendations, self.cache_timeouts['user_recommendations'])
            
            self.logger.info(f"Generated {len(recommendations)} content-based recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error in content-based recommendations for user {user_id}: {e}")
            return self._get_popular_movies_as_recommendations(limit)
    
    # HYBRID RECOMMENDATIONS
    
    def get_hybrid_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Hybrid recommendation algorithm combining multiple approaches.
        
        Args:
            user_id: Target user ID
            limit: Number of recommendations to return
            
        Returns:
            List of recommended movies with combined scores
        """
        cache_key = f'hybrid_recs_{user_id}_{limit}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        self.logger.info(f"Computing hybrid recommendations for user {user_id}")
        
        try:
            # Get recommendations from different algorithms
            user_collab_recs = self.get_user_based_recommendations(user_id, limit * 2)
            item_collab_recs = self.get_item_based_recommendations(user_id, limit * 2)
            content_recs = self.get_content_based_recommendations(user_id, limit * 2)
            popularity_recs = self._get_popularity_based_recommendations(user_id, limit)
            
            # Combine recommendations with weighted scores
            combined_scores = defaultdict(list)
            
            # Add collaborative filtering scores
            for rec in user_collab_recs:
                movie_id = rec['movie_id']
                weighted_score = rec['score'] * self.algorithm_weights['collaborative']
                combined_scores[movie_id].append(('user_collaborative', weighted_score))
            
            for rec in item_collab_recs:
                movie_id = rec['movie_id']
                weighted_score = rec['score'] * self.algorithm_weights['collaborative']
                combined_scores[movie_id].append(('item_collaborative', weighted_score))
            
            # Add content-based scores
            for rec in content_recs:
                movie_id = rec['movie_id']
                weighted_score = rec['score'] * self.algorithm_weights['content_based']
                combined_scores[movie_id].append(('content_based', weighted_score))
            
            # Add popularity scores
            for rec in popularity_recs:
                movie_id = rec['movie_id']
                weighted_score = rec['score'] * self.algorithm_weights['popularity']
                combined_scores[movie_id].append(('popularity', weighted_score))
            
            # Calculate final scores
            final_recommendations = []
            
            for movie_id, scores in combined_scores.items():
                # Calculate combined score (average of contributing algorithms)
                total_score = sum(score for _, score in scores)
                algorithm_count = len(scores)
                
                # Bonus for movies recommended by multiple algorithms
                diversity_bonus = 1.0 + (algorithm_count - 1) * 0.1
                final_score = total_score * diversity_bonus
                
                # Get algorithm sources
                algorithms = [alg for alg, _ in scores]
                
                final_recommendations.append({
                    'movie_id': movie_id,
                    'score': final_score,
                    'algorithm': 'hybrid',
                    'contributing_algorithms': algorithms,
                    'algorithm_count': algorithm_count
                })
            
            # Sort by final score and limit
            final_recommendations = sorted(
                final_recommendations, 
                key=lambda x: x['score'], 
                reverse=True
            )[:limit]
            
            # Enrich with movie data
            final_recommendations = self._enrich_recommendations_with_movie_data(final_recommendations)
            
            # Cache the results
            cache.set(cache_key, final_recommendations, self.cache_timeouts['user_recommendations'])
            
            self.logger.info(f"Generated {len(final_recommendations)} hybrid recommendations for user {user_id}")
            return final_recommendations
            
        except Exception as e:
            self.logger.error(f"Error in hybrid recommendations for user {user_id}: {e}")
            return self._get_popular_movies_as_recommendations(limit)
    
    # =================================================================
    # MOVIE SIMILARITY
    # =================================================================
    
    def get_similar_movies(self, movie_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find movies similar to the given movie.
        
        Args:
            movie_id: Source movie ID
            limit: Number of similar movies to return
            
        Returns:
            List of similar movies with similarity scores
        """
        cache_key = f'similar_movies_{movie_id}_{limit}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        self.logger.info(f"Finding similar movies to movie {movie_id}")
        
        try:
            similar_movies = self._find_similar_movies(movie_id, limit)
            similar_movies = self._enrich_recommendations_with_movie_data(similar_movies)
            
            # Cache the results
            cache.set(cache_key, similar_movies, self.cache_timeouts['similar_movies'])
            
            return similar_movies
            
        except Exception as e:
            self.logger.error(f"Error finding similar movies to {movie_id}: {e}")
            return []
    
    # =================================================================
    # USER INTERACTION LEARNING
    # =================================================================
    
    def record_user_interaction(self, user_id: int, movie_id: int, interaction_type: str, 
                               rating: Optional[float] = None, **kwargs):
        """
        Record user interaction for learning purposes.
        
        Args:
            user_id: User ID
            movie_id: Movie ID
            interaction_type: 'view', 'rating', 'favorite', 'watchlist'
            rating: Rating value (1-5) if applicable
            **kwargs: Additional interaction data
        """
        try:
            # Here you would save to your UserMovieInteraction model
            # This is placeholder - adjust based on your actual models
            
            self.logger.info(f"Recording {interaction_type} interaction: user {user_id}, movie {movie_id}")
            
            # Invalidate relevant caches
            self._invalidate_user_caches(user_id)
            
            # Update user preferences in real-time
            if interaction_type == 'rating' and rating:
                self._update_user_content_profile(user_id, movie_id, rating)
            
        except Exception as e:
            self.logger.error(f"Error recording user interaction: {e}")
    
    def update_user_preferences(self, user_id: int, movie_ratings: Dict[int, float]):
        """
        Bulk update user preferences based on multiple ratings.
        
        Args:
            user_id: User ID
            movie_ratings: Dictionary mapping movie_id to rating
        """
        try:
            self.logger.info(f"Updating preferences for user {user_id} with {len(movie_ratings)} ratings")
            
            for movie_id, rating in movie_ratings.items():
                self._update_user_content_profile(user_id, movie_id, rating)
            
            # Invalidate caches
            self._invalidate_user_caches(user_id)
            
        except Exception as e:
            self.logger.error(f"Error updating user preferences: {e}")
    
    # TRENDING AND CONTEXTUAL RECOMMENDATIONS
    
    def get_trending_recommendations(self, user_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending movies, optionally personalized for a user.
        
        Args:
            user_id: Optional user ID for personalization
            limit: Number of recommendations to return
            
        Returns:
            List of trending movies
        """
        cache_key = f'trending_recs_{user_id}_{limit}' if user_id else f'trending_recs_global_{limit}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Get base trending movies (high popularity in last 30 days)
            cutoff_date = timezone.now() - timedelta(days=30)
            
            trending_movies = Movie.objects.filter(
                release_date__gte=cutoff_date,
                tmdb_rating__gte=6.5
            ).order_by('-popularity_score', '-tmdb_rating')[:limit * 2]
            
            recommendations = []
            
            if user_id:
                # Personalize trending movies based on user preferences
                user_profile = self._build_user_content_profile(user_id)
                watched_movies = set(self._get_user_watched_movies(user_id))
                
                for movie in trending_movies:
                    if movie.id not in watched_movies:
                        # Score based on user preferences
                        content_score = self._calculate_content_similarity(user_profile, movie) if user_profile else 0.5
                        trending_score = float(movie.popularity_score) / 100.0  # Normalize
                        
                        combined_score = (content_score * 0.6) + (trending_score * 0.4)
                        
                        recommendations.append({
                            'movie_id': movie.id,
                            'score': combined_score,
                            'algorithm': 'trending_personalized',
                            'movie_data': {
                                'title': movie.title,
                                'year': movie.year,
                                'genres': movie.genre_names,
                                'tmdb_rating': float(movie.tmdb_rating) if movie.tmdb_rating else None,
                                'poster_url': movie.poster_url,
                                'popularity_score': float(movie.popularity_score)
                            }
                        })
            else:
                # Global trending movies
                for movie in trending_movies:
                    recommendations.append({
                        'movie_id': movie.id,
                        'score': float(movie.popularity_score) / 100.0,
                        'algorithm': 'trending_global',
                        'movie_data': {
                            'title': movie.title,
                            'year': movie.year,
                            'genres': movie.genre_names,
                            'tmdb_rating': float(movie.tmdb_rating) if movie.tmdb_rating else None,
                            'poster_url': movie.poster_url,
                            'popularity_score': float(movie.popularity_score)
                        }
                    })
            
            # Sort and limit
            recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:limit]
            
            # Cache results
            cache.set(cache_key, recommendations, self.cache_timeouts['user_recommendations'])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting trending recommendations: {e}")
            return []
    
    # HELPER METHODS - INTEGRATED WITH YOUR MODEL
    
    def _get_user_ratings(self, user_id: int) -> Dict[int, float]:
        """
        Get user's movie ratings using your UserMovieInteraction model.
        """
        from apps.recommendations.models import UserMovieInteraction
        
        ratings = UserMovieInteraction.objects.filter(
            user_id=user_id,
            interaction_type='rating',
            rating__isnull=False
        ).values_list('movie_id', 'rating')
        
        return dict(ratings)
    
    def _get_user_high_rated_movies(self, user_id: int, min_rating: float = 4.0) -> Dict[int, float]:
        """Get movies rated highly by user."""
        from apps.recommendations.models import UserMovieInteraction
        
        high_rated = UserMovieInteraction.objects.filter(
            user_id=user_id,
            interaction_type='rating',
            rating__gte=min_rating
        ).values_list('movie_id', 'rating')
        
        return dict(high_rated)
    
    def _get_user_watched_movies(self, user_id: int) -> List[int]:
        """Get list of movies user has interacted with."""
        from apps.recommendations.models import UserMovieInteraction
        
        return list(UserMovieInteraction.objects.filter(
            user_id=user_id
        ).values_list('movie_id', flat=True).distinct())
    
    def _find_similar_users(self, user_id: int, user_ratings: Dict[int, float]) -> List[Tuple[int, float]]:
        """Find users with similar rating patterns using your existing method."""
        from apps.recommendations.models import UserMovieInteraction
        
        try:
            # Use your existing method from UserMovieInteraction
            similar_user_ids = UserMovieInteraction.get_similar_users(
                User.objects.get(id=user_id), 
                min_common_movies=self.min_common_items
            )
            
            # Calculate similarity scores (simplified)
            similar_users = []
            for similar_user_id in similar_user_ids[:20]:  # Limit for performance
                similarity_score = self._calculate_user_similarity(user_id, similar_user_id, user_ratings)
                if similarity_score > self.min_similarity_threshold:
                    similar_users.append((similar_user_id, similarity_score))
            
            return sorted(similar_users, key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding similar users: {e}")
            return []
    
    def _calculate_user_similarity(self, user1_id: int, user2_id: int, user1_ratings: Dict[int, float]) -> float:
        """Calculate similarity between two users using cosine similarity."""
        from apps.recommendations.models import UserMovieInteraction
        
        # Get user2's ratings
        user2_ratings = self._get_user_ratings(user2_id)
        
        # Find common movies
        common_movies = set(user1_ratings.keys()) & set(user2_ratings.keys())
        
        if len(common_movies) < self.min_common_items:
            return 0.0
        
        # Calculate cosine similarity
        dot_product = sum(user1_ratings[movie] * user2_ratings[movie] for movie in common_movies)
        
        norm1 = math.sqrt(sum(user1_ratings[movie] ** 2 for movie in common_movies))
        norm2 = math.sqrt(sum(user2_ratings[movie] ** 2 for movie in common_movies))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _find_similar_movies(self, movie_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Find movies similar to the given movie based on content features."""
        try:
            source_movie = Movie.objects.get(id=movie_id)
            
            # Find movies with similar genres, cast, director
            similar_movies = Movie.objects.filter(
                ~Q(id=movie_id),
                genres__in=source_movie.genres.all()
            ).distinct().annotate(
                common_genres=Count('genres', filter=Q(genres__in=source_movie.genres.all()))
            ).order_by('-common_genres', '-tmdb_rating')[:limit]
            
            recommendations = []
            for movie in similar_movies:
                # Simple similarity based on common genres
                similarity = movie.common_genres / max(source_movie.genres.count(), 1)
                
                recommendations.append({
                    'movie_id': movie.id,
                    'similarity': similarity,
                    'score': similarity,
                    'algorithm': 'content_similarity'
                })
            
            return recommendations
            
        except Movie.DoesNotExist:
            return []
    
    def _build_user_content_profile(self, user_id: int) -> Dict[str, Any]:
        """Build user's content preference profile using your UserMovieInteraction model."""
        from apps.recommendations.models import UserMovieInteraction
        
        try:
            user = User.objects.get(id=user_id)
            
            # Use your existing method to get preferred genres
            preferred_genres = UserMovieInteraction.get_user_preferred_genres(user, limit=10)
            
            # Get user's rating patterns
            user_ratings = self._get_user_ratings(user_id)
            
            # Calculate average rating
            avg_rating = sum(user_ratings.values()) / len(user_ratings) if user_ratings else 3.0
            
            # Get positive interactions for additional preferences
            positive_interactions = UserMovieInteraction.objects.filter(
                user_id=user_id,
                interaction_type__in=['like', 'favorite', 'watchlist']
            ).select_related('movie')
            
            # Extract director preferences
            director_preferences = Counter()
            actor_preferences = Counter()
            language_preferences = Counter()
            
            for interaction in positive_interactions:
                movie = interaction.movie
                weight = interaction.engagement_weight
                
                if movie.director:
                    director_preferences[movie.director] += weight
                
                if movie.main_cast_list:
                    for actor in movie.main_cast_list[:3]:  # Top 3 actors
                        actor_preferences[actor] += weight
                
                if movie.original_language:
                    language_preferences[movie.original_language] += weight
            
            # Build profile
            profile = {
                'preferred_genres': [genre.name for genre in preferred_genres],
                'genre_weights': {genre.name: 1.0 for genre in preferred_genres},  # You could make this more sophisticated
                'preferred_directors': dict(director_preferences.most_common(10)),
                'preferred_actors': dict(actor_preferences.most_common(15)),
                'preferred_languages': dict(language_preferences.most_common(5)),
                'avg_rating': avg_rating,
                'total_interactions': len(user_ratings),
                'rating_distribution': self._calculate_rating_distribution(user_ratings)
            }
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error building user content profile for user {user_id}: {e}")
            return {}
    
    def _calculate_rating_distribution(self, ratings: Dict[int, float]) -> Dict[str, float]:
        """Calculate user's rating distribution."""
        if not ratings:
            return {}
        
        rating_counts = Counter()
        for rating in ratings.values():
            rating_counts[int(rating)] += 1
        
        total = len(ratings)
        return {str(k): v/total for k, v in rating_counts.items()}
    
    def _calculate_content_similarity(self, user_profile: Dict[str, Any], movie: Movie) -> float:
        """Calculate similarity between user profile and movie content."""
        if not user_profile:
            return 0.5  # Neutral score
        
        similarity_score = 0.0
        weight_sum = 0.0
        
        # Genre similarity (40% weight)
        genre_weight = 0.4
        preferred_genres = set(user_profile.get('preferred_genres', []))
        movie_genres = set(movie.genre_names)
        
        if preferred_genres and movie_genres:
            genre_overlap = len(preferred_genres & movie_genres)
            genre_similarity = genre_overlap / len(preferred_genres | movie_genres)
            similarity_score += genre_similarity * genre_weight
            weight_sum += genre_weight
        
        # Director similarity (20% weight)
        director_weight = 0.2
        preferred_directors = user_profile.get('preferred_directors', {})
        if movie.director and movie.director in preferred_directors:
            director_score = min(1.0, preferred_directors[movie.director] / 10.0)  # Normalize
            similarity_score += director_score * director_weight
            weight_sum += director_weight
        
        # Cast similarity (25% weight)
        cast_weight = 0.25
        preferred_actors = user_profile.get('preferred_actors', {})
        movie_cast = set(movie.main_cast_list) if movie.main_cast_list else set()
        
        if preferred_actors and movie_cast:
            cast_score = 0.0
            for actor in movie_cast:
                if actor in preferred_actors:
                    cast_score += min(1.0, preferred_actors[actor] / 10.0)  # Normalize
            
            # Average over movie cast size
            cast_similarity = min(1.0, cast_score / len(movie_cast))
            similarity_score += cast_similarity * cast_weight
            weight_sum += cast_weight
        
        # Rating compatibility (15% weight)
        rating_weight = 0.15
        user_avg_rating = user_profile.get('avg_rating', 3.0)
        if movie.tmdb_rating:
            movie_rating = float(movie.tmdb_rating)
            # Score based on how close movie rating is to user's average preference
            rating_diff = abs(movie_rating - user_avg_rating)
            rating_similarity = max(0.0, 1.0 - (rating_diff / 5.0))  # Normalize to 0-1
            similarity_score += rating_similarity * rating_weight
            weight_sum += rating_weight
        
        # Normalize by total weights used
        final_score = similarity_score / weight_sum if weight_sum > 0 else 0.5
        
        return min(1.0, max(0.0, final_score))
    
    def _get_popular_movies_as_recommendations(self, limit: int) -> List[Dict[str, Any]]:
        """Fallback to popular movies when personalized recommendations fail."""
        popular_movies = Movie.objects.filter(
            tmdb_rating__gte=7.0
        ).order_by('-popularity_score', '-tmdb_rating')[:limit]
        
        recommendations = []
        for movie in popular_movies:
            recommendations.append({
                'movie_id': movie.id,
                'score': float(movie.popularity_score) / 100.0,
                'algorithm': 'popularity_fallback',
                'movie_data': {
                    'title': movie.title,
                    'year': movie.year,
                    'genres': movie.genre_names,
                    'tmdb_rating': float(movie.tmdb_rating) if movie.tmdb_rating else None,
                    'poster_url': movie.poster_url
                }
            })
        
        return recommendations
    
    def _get_popularity_based_recommendations(self, user_id: int, limit: int) -> List[Dict[str, Any]]:
        """Get recommendations based on overall popularity."""
        return self._get_popular_movies_as_recommendations(limit)
    
    def _get_recommendations_from_similar_users(self, user_id: int, similar_users: List[Tuple[int, float]], limit: int) -> List[Dict[str, Any]]:
        """Get recommendations from similar users."""
        from apps.recommendations.models import UserMovieInteraction
        
        recommendations = defaultdict(list)
        watched_movies = set(self._get_user_watched_movies(user_id))
        
        for similar_user_id, similarity_score in similar_users[:10]:  # Top 10 similar users
            # Get highly rated movies from similar user
            similar_user_ratings = self._get_user_high_rated_movies(similar_user_id, min_rating=4.0)
            
            for movie_id, rating in similar_user_ratings.items():
                if movie_id not in watched_movies:
                    # Weight the rating by user similarity
                    weighted_score = (rating / 5.0) * similarity_score
                    recommendations[movie_id].append(weighted_score)
        
        # Aggregate scores for movies recommended by multiple similar users
        final_recommendations = []
        for movie_id, scores in recommendations.items():
            # Average score with bonus for multiple recommendations
            avg_score = sum(scores) / len(scores)
            consensus_bonus = 1.0 + (len(scores) - 1) * 0.1  # Bonus for multiple similar users
            final_score = min(1.0, avg_score * consensus_bonus)
            
            final_recommendations.append({
                'movie_id': movie_id,
                'score': final_score,
                'algorithm': 'user_collaborative',
                'recommendation_count': len(scores)
            })
        
        return sorted(final_recommendations, key=lambda x: x['score'], reverse=True)[:limit]
    
    def _store_recommendations(self, user_id: int, recommendations: List[Dict[str, Any]], algorithm: str):
        """Store recommendations using your UserRecommendations model."""
        from apps.recommendations.models import UserRecommendations
        
        stored_recommendations = []
        
        for rec in recommendations:
            try:
                # Check if recommendation already exists
                existing = UserRecommendations.objects.filter(
                    user_id=user_id,
                    movie_id=rec['movie_id'],
                    algorithm=algorithm
                ).first()
                
                if existing:
                    # Update score if different
                    if abs(existing.score - rec['score']) > 0.01:
                        existing.score = rec['score']
                        existing.save()
                else:
                    # Create new recommendation
                    new_rec = UserRecommendations.objects.create(
                        user_id=user_id,
                        movie_id=rec['movie_id'],
                        score=rec['score'],
                        algorithm=algorithm
                    )
                    stored_recommendations.append(new_rec)
                    
            except Exception as e:
                self.logger.error(f"Error storing recommendation: {e}")
                continue
        
        return stored_recommendations
    
    def _aggregate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate recommendations that appear multiple times."""
        aggregated = defaultdict(list)
        
        for rec in recommendations:
            movie_id = rec['movie_id']
            aggregated[movie_id].append(rec['score'])
        
        result = []
        for movie_id, scores in aggregated.items():
            avg_score = sum(scores) / len(scores)
            result.append({
                'movie_id': movie_id,
                'score': avg_score,
                'recommendation_count': len(scores)
            })
        
        return result
    
    def _enrich_recommendations_with_movie_data(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add movie details to recommendations."""
        movie_ids = [rec['movie_id'] for rec in recommendations]
        movies = Movie.objects.filter(id__in=movie_ids)
        movie_dict = {movie.id: movie for movie in movies}
        
        enriched = []
        for rec in recommendations:
            movie = movie_dict.get(rec['movie_id'])
            if movie:
                rec['movie_data'] = {
                    'title': movie.title,
                    'year': movie.year,
                    'genres': movie.genre_names,
                    'tmdb_rating': float(movie.tmdb_rating) if movie.tmdb_rating else None,
                    'poster_url': movie.poster_url,
                    'overview': movie.overview
                }
                enriched.append(rec)
        
        return enriched
    
    def _invalidate_user_caches(self, user_id: int):
        """Invalidate all caches related to a user."""
        cache_patterns = [
            f'user_collab_recs_{user_id}_*',
            f'item_collab_recs_{user_id}_*',
            f'content_recs_{user_id}_*',
            f'hybrid_recs_{user_id}_*',
            f'trending_recs_{user_id}_*'
        ]
        
        # Note: Django cache doesn't support pattern deletion by default
        # You might need django-redis or implement a cache key tracking system
        for pattern in cache_patterns:
            try:
                cache.delete(pattern)
            except:
                pass

    # A/B TESTING INTEGRATION
    
    def get_recommendations_with_ab_testing(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recommendations with A/B testing integration using your experiment framework.
        """
        from apps.recommendations.models import RecommendationExperiment
        
        try:
            user = User.objects.get(id=user_id)
            
            # Check for active experiment
            active_experiment = RecommendationExperiment.get_active_experiment()
            
            if active_experiment:
                # Get algorithm based on experiment assignment
                algorithm = active_experiment.get_algorithm_for_user(user)
                self.logger.info(f"User {user_id} assigned to algorithm '{algorithm}' via experiment '{active_experiment.name}'")
            else:
                # Use default hybrid algorithm
                algorithm = 'hybrid'
            
            # Get recommendations based on assigned algorithm
            if algorithm == 'collaborative':
                recommendations = self.get_user_based_recommendations(user_id, limit)
            elif algorithm == 'content_based':
                recommendations = self.get_content_based_recommendations(user_id, limit)
            elif algorithm == 'hybrid':
                recommendations = self.get_hybrid_recommendations(user_id, limit)
            elif algorithm == 'trending':
                recommendations = self.get_trending_recommendations(user_id, limit)
            else:
                # Fallback to hybrid
                recommendations = self.get_hybrid_recommendations(user_id, limit)
            
            # Store recommendations with the algorithm used
            self._store_recommendations(user_id, recommendations, algorithm)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error in A/B testing recommendations for user {user_id}: {e}")
            return self.get_hybrid_recommendations(user_id, limit)
 
    # INTEGRATION WITH YOUR EXISTING TRENDING SYSTEm
    
    def get_trending_recommendations(self, user_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending movies using your existing UserMovieInteraction.get_trending_movies method.
        """
        from apps.recommendations.models import UserMovieInteraction
        
        cache_key = f'trending_recs_{user_id}_{limit}' if user_id else f'trending_recs_global_{limit}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Use your existing trending movies method
            trending_data = UserMovieInteraction.get_trending_movies(
                days=7,
                interaction_types=['view', 'like', 'favorite', 'rating']
            )
            
            recommendations = []
            watched_movies = set(self._get_user_watched_movies(user_id)) if user_id else set()
            
            for trend_item in trending_data[:limit * 2]:  # Get more to filter
                movie_id = trend_item['movie']
                
                # Skip if user already watched this movie
                if user_id and movie_id in watched_movies:
                    continue
                
                try:
                    movie = Movie.objects.get(id=movie_id)
                    
                    # Calculate trending score
                    interaction_count = trend_item['interaction_count']
                    unique_users = trend_item['unique_users']
                    
                    # Combine interaction count and user diversity
                    trending_score = (interaction_count * 0.6) + (unique_users * 0.4)
                    # Normalize to 0-1 scale
                    normalized_score = min(1.0, trending_score / 100.0)
                    
                    # Personalize if user provided
                    if user_id:
                        user_profile = self._build_user_content_profile(user_id)
                        if user_profile:
                            content_score = self._calculate_content_similarity(user_profile, movie)
                            # Combine trending and personal preference
                            final_score = (normalized_score * 0.6) + (content_score * 0.4)
                        else:
                            final_score = normalized_score
                    else:
                        final_score = normalized_score
                    
                    recommendations.append({
                        'movie_id': movie_id,
                        'score': final_score,
                        'algorithm': 'trending_personalized' if user_id else 'trending_global',
                        'movie_data': {
                            'title': movie.title,
                            'year': movie.year,
                            'genres': movie.genre_names,
                            'tmdb_rating': float(movie.tmdb_rating) if movie.tmdb_rating else None,
                            'poster_url': movie.poster_url,
                            'interaction_count': interaction_count,
                            'unique_users': unique_users
                        }
                    })
                    
                    if len(recommendations) >= limit:
                        break
                        
                except Movie.DoesNotExist:
                    continue
            
            # Sort by score
            recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:limit]
            
            # Cache results
            cache.set(cache_key, recommendations, self.cache_timeouts['user_recommendations'])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting trending recommendations: {e}")
            return self._get_popular_movies_as_recommendations(limit)
    
    # =================================================================
    # INTEGRATION WITH YOUR INTERACTION TRACKING
    # =================================================================
    
    def record_user_interaction(self, user_id: int, movie_id: int, interaction_type: str, 
                               rating: Optional[float] = None, source: str = 'web', **kwargs):
        """
        Record user interaction using your UserMovieInteraction model.
        """
        from apps.recommendations.models import UserMovieInteraction
        
        try:
            user = User.objects.get(id=user_id)
            movie = Movie.objects.get(id=movie_id)
            
            # Use your model's create_interaction method
            interaction = UserMovieInteraction.create_interaction(
                user=user,
                movie=movie,
                interaction_type=interaction_type,
                source=source,
                rating=rating,
                **kwargs
            )
            
            self.logger.info(f"Recorded {interaction_type} interaction: user {user_id}, movie {movie_id}")
            
            # Invalidate relevant caches
            self._invalidate_user_caches(user_id)
            
            # If this was a recommendation click, mark it in UserRecommendations
            if interaction_type == 'recommendation_click':
                self._mark_recommendation_clicked(user_id, movie_id, kwargs.get('algorithm'))
            
            return interaction
            
        except Exception as e:
            self.logger.error(f"Error recording user interaction: {e}")
            return None
    
    def _mark_recommendation_clicked(self, user_id: int, movie_id: int, algorithm: Optional[str] = None):
        """Mark recommendation as clicked in your UserRecommendations model."""
        from apps.recommendations.models import UserRecommendations
        
        try:
            query = {'user_id': user_id, 'movie_id': movie_id}
            if algorithm:
                query['algorithm'] = algorithm
            
            recommendation = UserRecommendations.objects.filter(**query).first()
            if recommendation:
                recommendation.mark_as_clicked()
                
        except Exception as e:
            self.logger.error(f"Error marking recommendation as clicked: {e}")
    
    # =================================================================
    # PERFORMANCE ANALYTICS USING YOUR MODELS
    # =================================================================
    
    def get_recommendation_performance(self, algorithm: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get recommendation performance analytics using your UserRecommendations model.
        """
        from apps.recommendations.models import UserRecommendations
        
        try:
            if algorithm:
                performance = UserRecommendations.get_algorithm_performance(algorithm, days)
            else:
                # Get performance for all algorithms
                algorithms = UserRecommendations.objects.values_list('algorithm', flat=True).distinct()
                performance = {}
                
                for alg in algorithms:
                    performance[alg] = UserRecommendations.get_algorithm_performance(alg, days)
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Error getting recommendation performance: {e}")
            return {}
    
    def cleanup_old_recommendations(self, days: int = 30) -> int:
        """
        Clean up old recommendations using your model's cleanup method.
        """
        from apps.recommendations.models import UserRecommendations
        
        try:
            return UserRecommendations.cleanup_old_recommendations(days)
        except Exception as e:
            self.logger.error(f"Error cleaning up old recommendations: {e}")
            return 0

# =================================================================
# CONVENIENCE FUNCTIONS
# =================================================================

def get_recommendation_service() -> RecommendationService:
    """
    Get a configured recommendation service instance.
    
    Returns:
        RecommendationService instance
    """
    return RecommendationService()
