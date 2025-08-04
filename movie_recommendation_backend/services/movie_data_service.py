"""
Movie Data Service - Combines TMDB and OMDB APIs

This service orchestrates data from both TMDB and OMDB APIs to provide
comprehensive movie information with multiple ratings sources.
"""

import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db import transaction

from .tmdb_service import get_tmdb_service
from .omdb_service import get_omdb_service

logger = logging.getLogger(__name__)

# MOVIE DATA SERVICE - ORCHESTRATES MULTIPLE APIs
class MovieDataService:
    """
    High-level service that combines TMDB and OMDB data to provide
    comprehensive movie information.
    
    Features:
    - Data enrichment from multiple sources
    - Intelligent fallback strategies
    - Bulk operations with rate limiting
    - Database synchronization helpers
    """
    
    def __init__(self):
        """Initialize the movie data service."""
        self.tmdb = get_tmdb_service()
        self.omdb = get_omdb_service()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.logger.info("Movie Data Service initialized")

    # HEALTH CHECK AND MONITORING

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all underlying services.
        
        Returns:
            Combined health status
        """
        tmdb_health = self.tmdb.health_check()
        omdb_health = self.omdb.health_check()
        
        overall_healthy = (
            tmdb_health['status'] == 'healthy' and 
            omdb_health['status'] == 'healthy'
        )
        
        return {
            'service': 'MovieDataService',
            'status': 'healthy' if overall_healthy else 'degraded',
            'services': {
                'tmdb': tmdb_health,
                'omdb': omdb_health
            },
            'timestamp': timezone.now().isoformat()
        }

    # MOVIE DISCOVERY AND SEARCH
    
    def get_popular_movies_enriched(self, pages: int = 5) -> List[Dict[str, Any]]:
        """
        Get popular movies from TMDB enriched with OMDB ratings.
        
        Args:
            pages: Number of TMDB pages to fetch
            
        Returns:
            List of enriched movie data
        """
        self.logger.info(f"Fetching popular movies with enrichment ({pages} pages)")
        
        # Get popular movies from TMDB
        tmdb_movies = self.tmdb.get_movies_by_pages('popular_movies', pages)
        
        # Enrich with OMDB data
        enriched_movies = self.omdb.enrich_tmdb_movies(tmdb_movies)
        
        self.logger.info(f"Retrieved {len(enriched_movies)} popular movies with enrichment")
        return enriched_movies
    
    def get_top_rated_movies_enriched(self, pages: int = 5) -> List[Dict[str, Any]]:
        """
        Get top-rated movies from TMDB enriched with OMDB ratings.
        
        Args:
            pages: Number of TMDB pages to fetch
            
        Returns:
            List of enriched movie data
        """
        self.logger.info(f"Fetching top-rated movies with enrichment ({pages} pages)")
        
        # Get top-rated movies from TMDB
        tmdb_movies = self.tmdb.get_movies_by_pages('top_rated_movies', pages)
        
        # Enrich with OMDB data
        enriched_movies = self.omdb.enrich_tmdb_movies(tmdb_movies)
        
        self.logger.info(f"Retrieved {len(enriched_movies)} top-rated movies with enrichment")
        return enriched_movies
    
    def search_movies_comprehensive(self, query: str, include_omdb: bool = True) -> List[Dict[str, Any]]:
        """
        Search movies across both TMDB and optionally OMDB.
        
        Args:
            query: Search query
            include_omdb: Whether to enrich with OMDB data
            
        Returns:
            List of search results
        """
        self.logger.info(f"Comprehensive movie search: '{query}'")
        
        # Search TMDB first (more comprehensive)
        tmdb_results = self.tmdb.search_movies(query)
        tmdb_movies = tmdb_results.get('results', [])
        
        if not include_omdb:
            return tmdb_movies
        
        # Enrich with OMDB data (rate-limited)
        enriched_movies = self.omdb.enrich_tmdb_movies(tmdb_movies[:10])  # Limit to 10 for search
        
        self.logger.info(f"Found {len(enriched_movies)} movies for query: '{query}'")
        return enriched_movies

    # INDIVIDUAL MOVIE DATA
    
    def get_complete_movie_data(self, tmdb_id: int) -> Dict[str, Any]:
        """
        Get complete movie data from all sources.
        
        Args:
            tmdb_id: TMDB movie ID
            
        Returns:
            Complete movie data with all available information
        """
        self.logger.info(f"Fetching complete movie data for TMDB ID: {tmdb_id}")
        
        # Get detailed TMDB data
        movie_details = self.tmdb.get_movie_details(tmdb_id)
        if not movie_details:
            return {}
        
        # Get credits data
        credits = self.tmdb.get_movie_credits(tmdb_id)
        
        # Extract cast and crew
        director = self.tmdb.extract_director(credits)
        main_cast = self.tmdb.extract_main_cast(credits)
        
        # Get OMDB data for additional ratings
        omdb_data = self.omdb.get_movie_by_tmdb_data(movie_details)
        
        # Combine all data
        complete_data = {
            # TMDB core data
            'tmdb_data': movie_details,
            'tmdb_credits': credits,
            
            # Extracted information
            'director': director,
            'main_cast': main_cast,
            'genres': self.tmdb.extract_genre_names(movie_details),
            'production_companies': self.tmdb.extract_production_companies(movie_details),
            
            # Image URLs
            'poster_url': self.tmdb.get_poster_url(movie_details.get('poster_path')),
            'backdrop_url': self.tmdb.get_backdrop_url(movie_details.get('backdrop_path')),
            
            # OMDB enrichment
            'omdb_data': {},
            'omdb_ratings': {},
            'omdb_additional_info': {}
        }
        
        # Add OMDB data if available
        if omdb_data and self.omdb.is_valid_response(omdb_data):
            complete_data.update({
                'omdb_data': omdb_data,
                'omdb_ratings': self.omdb.extract_ratings(omdb_data),
                'omdb_additional_info': self.omdb.extract_additional_info(omdb_data)
            })
        
        self.logger.info(f"Retrieved complete data for: {movie_details.get('title')}")
        return complete_data
    
    # BULK OPERATIONS
    
    def get_multiple_movies_complete(self, tmdb_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get complete movie data for multiple movies.
        
        Args:
            tmdb_ids: List of TMDB movie IDs
            
        Returns:
            List of complete movie data
        """
        self.logger.info(f"Fetching complete data for {len(tmdb_ids)} movies")
        
        complete_movies = []
        
        for tmdb_id in tmdb_ids:
            try:
                complete_data = self.get_complete_movie_data(tmdb_id)
                if complete_data:
                    complete_movies.append(complete_data)
                    
            except Exception as e:
                self.logger.error(f"Failed to get complete data for movie {tmdb_id}: {e}")
                continue
        
        self.logger.info(f"Retrieved complete data for {len(complete_movies)} movies")
        return complete_movies

    # DATABASE SYNCHRONIZATION HELPERS
    
    def prepare_movie_for_database(self, complete_movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform complete movie data into format suitable for database storage.
        
        Args:
            complete_movie_data: Complete movie data from get_complete_movie_data()
            
        Returns:
            Dictionary formatted for Django model creation
        """
        tmdb_data = complete_movie_data.get('tmdb_data', {})
        omdb_ratings = complete_movie_data.get('omdb_ratings', {})
        omdb_info = complete_movie_data.get('omdb_additional_info', {})
        
        # Parse release date
        release_date = None
        release_date_str = tmdb_data.get('release_date')
        if release_date_str:
            try:
                from datetime import datetime
                release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Prepare database fields
        db_data = {
            # TMDB data
            'tmdb_id': tmdb_data.get('id'),
            'imdb_id': tmdb_data.get('imdb_id'),
            'title': tmdb_data.get('title', ''),
            'original_title': tmdb_data.get('original_title', ''),
            'overview': tmdb_data.get('overview', ''),
            'tagline': tmdb_data.get('tagline', ''),
            'release_date': release_date,
            'runtime': tmdb_data.get('runtime'),
            'director': complete_movie_data.get('director', ''),
            'main_cast': complete_movie_data.get('main_cast', []),
            
            # Ratings
            'tmdb_rating': tmdb_data.get('vote_average'),
            'tmdb_vote_count': tmdb_data.get('vote_count', 0),
            'omdb_imdb_rating': omdb_ratings.get('imdb_rating'),
            'omdb_rotten_tomatoes_rating': omdb_ratings.get('rotten_tomatoes_rating'),
            'omdb_metacritic_rating': omdb_ratings.get('metacritic_rating'),
            
            # Media
            'poster_path': tmdb_data.get('poster_path', ''),
            'backdrop_path': tmdb_data.get('backdrop_path', ''),
            
            # Metadata
            'popularity_score': tmdb_data.get('popularity', 0.0),
            'adult': tmdb_data.get('adult', False),
            'original_language': tmdb_data.get('original_language', 'en'),
            'status': tmdb_data.get('status', 'released').lower(),
            
            # Store raw data for future use
            'external_data': {
                'tmdb': tmdb_data,
                'omdb': complete_movie_data.get('omdb_data', {}),
                'last_updated': timezone.now().isoformat()
            }
        }
        
        return db_data
    
    def sync_movies_to_database(self, movie_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Sync multiple movies to the database.
        
        Args:
            movie_data_list: List of complete movie data
            
        Returns:
            Statistics about the sync operation
        """
        from apps.movies.models import Movie, Genre, MovieGenre
        
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'genres_processed': 0
        }
        
        self.logger.info(f"Starting database sync for {len(movie_data_list)} movies")
        
        for movie_data in movie_data_list:
            try:
                with transaction.atomic():
                    # Prepare database data
                    db_data = self.prepare_movie_for_database(movie_data)
                    
                    if not db_data.get('tmdb_id'):
                        stats['errors'] += 1
                        continue
                    
                    # Create or update movie
                    movie, created = Movie.objects.update_or_create(
                        tmdb_id=db_data['tmdb_id'],
                        defaults=db_data
                    )
                    
                    # Update genre relationships
                    tmdb_data = movie_data.get('tmdb_data', {})
                    if 'genres' in tmdb_data:
                        genre_ids = [g['id'] for g in tmdb_data['genres']]
                        genres = Genre.objects.filter(tmdb_id__in=genre_ids)
                        movie.genres.set(genres)
                        stats['genres_processed'] += len(genres)
                    
                    # Mark as synced
                    movie.mark_synced('combined')
                    
                    if created:
                        stats['created'] += 1
                        self.logger.debug(f"Created movie: {movie.title}")
                    else:
                        stats['updated'] += 1
                        self.logger.debug(f"Updated movie: {movie.title}")
                        
            except Exception as e:
                self.logger.error(f"Failed to sync movie: {e}")
                stats['errors'] += 1
                continue
        
        self.logger.info(f"Database sync completed: {stats}")
        return stats
    
    # GENRE SYNCHRONIZATION
    def sync_genres_to_database(self) -> int:
        """
        Sync genres from TMDB to database.
        
        Returns:
            Number of genres synced
        """
        from apps.movies.models import Genre
        
        self.logger.info("Syncing genres from TMDB")
        
        # Get genres from TMDB
        genres_data = self.tmdb.get_genres()
        
        synced_count = 0
        
        with transaction.atomic():
            for genre_data in genres_data:
                genre, created = Genre.objects.update_or_create(
                    tmdb_id=genre_data['id'],
                    defaults={
                        'name': genre_data['name']
                    }
                )
                
                synced_count += 1
                
                if created:
                    self.logger.debug(f"Created genre: {genre.name}")
                else:
                    self.logger.debug(f"Updated genre: {genre.name}")
        
        self.logger.info(f"Synced {synced_count} genres")
        return synced_count
    
    # CONVENIENCE METHODS
    
    def seed_database(self, 
                     popular_pages: int = 10, 
                     top_rated_pages: int = 5,
                     sync_genres: bool = True) -> Dict[str, Any]:
        """
        Seed the database with movies from both APIs.
        
        Args:
            popular_pages: Number of popular movie pages to fetch
            top_rated_pages: Number of top-rated movie pages to fetch
            sync_genres: Whether to sync genres first
            
        Returns:
            Seeding statistics
        """
        self.logger.info("Starting database seeding operation")
        
        total_stats = {
            'genres_synced': 0,
            'movies_created': 0,
            'movies_updated': 0,
            'errors': 0,
            'start_time': timezone.now()
        }
        
        try:
            # Sync genres first
            if sync_genres:
                total_stats['genres_synced'] = self.sync_genres_to_database()
            
            # Get and sync popular movies
            popular_movies = self.get_popular_movies_enriched(popular_pages)
            popular_stats = self.sync_movies_to_database(popular_movies)
            
            # Get and sync top-rated movies
            top_rated_movies = self.get_top_rated_movies_enriched(top_rated_pages)
            top_rated_stats = self.sync_movies_to_database(top_rated_movies)
            
            # Combine statistics
            total_stats.update({
                'movies_created': popular_stats['created'] + top_rated_stats['created'],
                'movies_updated': popular_stats['updated'] + top_rated_stats['updated'],
                'errors': popular_stats['errors'] + top_rated_stats['errors'],
                'end_time': timezone.now()
            })
            
            # Calculate duration
            duration = total_stats['end_time'] - total_stats['start_time']
            total_stats['duration_seconds'] = duration.total_seconds()
            
            self.logger.info(f"Database seeding completed: {total_stats}")
            
        except Exception as e:
            self.logger.error(f"Database seeding failed: {e}")
            total_stats['fatal_error'] = str(e)
        
        return total_stats

# CONVENIENCE FUNCTIONS

def get_movie_data_service() -> MovieDataService:
    """
    Get a configured movie data service instance.
    
    Returns:
        MovieDataService instance
    """
    return MovieDataService()
