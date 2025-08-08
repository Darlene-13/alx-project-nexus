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
        Fixed to handle all validation requirements.
        """
        # Handle different possible data structures
        tmdb_data = complete_movie_data.get('tmdb_data', {})
        
        # If tmdb_data is empty, try the root level (direct TMDB response)
        if not tmdb_data:
            tmdb_data = complete_movie_data
        
        omdb_ratings = complete_movie_data.get('omdb_ratings', {})
        omdb_info = complete_movie_data.get('omdb_additional_info', {})
        
        # Extract TMDB ID more reliably
        tmdb_id = tmdb_data.get('id') or complete_movie_data.get('id')
        
        # Debug logging
        print(f"  🔍 complete_movie_data keys: {list(complete_movie_data.keys())}")
        print(f"  🔍 tmdb_data keys: {list(tmdb_data.keys())}")
        print(f"  🔍 extracted tmdb_id: {tmdb_id}")
        print(f"  🔍 movie title: {tmdb_data.get('title', 'No title')}")
        
        if not tmdb_id:
            print(f"  ❌ WARNING: No TMDB ID found in data structure!")
            return {}
        
        # Parse release date
        release_date = None
        release_date_str = tmdb_data.get('release_date')
        if release_date_str:
            try:
                from datetime import datetime
                release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # ✅ FIXED: Format ratings to proper decimal places
        tmdb_rating = tmdb_data.get('vote_average')
        if tmdb_rating is not None:
            tmdb_rating = round(float(tmdb_rating), 1)  # 1 decimal place
        
        omdb_rating = omdb_ratings.get('imdb_rating') if omdb_ratings else None
        if omdb_rating is not None:
            omdb_rating = round(float(omdb_rating), 1)  # 1 decimal place
        
        # ✅ FIXED: Format popularity to 2 decimal places
        popularity = tmdb_data.get('popularity', 0.0)
        if popularity is not None:
            popularity = round(float(popularity), 2)  # 2 decimal places
        
        # ✅ FIXED: Handle main_cast properly - provide default non-empty list if empty
        main_cast = complete_movie_data.get('main_cast', [])
        if not main_cast or main_cast == []:
            # If no cast data, use a placeholder to satisfy the "cannot be blank" requirement
            main_cast = ["Cast information not available"]
        
        # Build database data with fixed validation issues
        db_data = {
            'tmdb_id': tmdb_id,
            'title': tmdb_data.get('title', ''),
            'original_title': tmdb_data.get('original_title', ''),
            'overview': tmdb_data.get('overview', ''),
            'tagline': tmdb_data.get('tagline', ''),
            'release_date': release_date,
            'runtime': tmdb_data.get('runtime'),
            'director': complete_movie_data.get('director', ''),
            'main_cast': main_cast,  # ✅ FIXED: Never empty
            'tmdb_rating': tmdb_rating,  # ✅ FIXED: 1 decimal place
            'tmdb_vote_count': tmdb_data.get('vote_count', 0),
            'omdb_rating': omdb_rating,  # ✅ FIXED: 1 decimal place  
            'poster_path': tmdb_data.get('poster_path', ''),
            'backdrop_path': tmdb_data.get('backdrop_path', ''),
            'popularity_score': popularity,  # ✅ FIXED: 2 decimal places
            'adult': tmdb_data.get('adult', False),
            'original_language': tmdb_data.get('original_language', 'en'),
            'views': 0,
            'like_count': 0,
        }
        
        # Only remove None values for optional fields, keep required fields always
        required_fields = {'tmdb_id', 'title', 'original_title', 'main_cast'}
        filtered_data = {}
        
        for key, value in db_data.items():
            if key in required_fields or value is not None:
                filtered_data[key] = value
        
        print(f"  ✅ Final DB data keys: {list(filtered_data.keys())}")
        print(f"  ✅ Final tmdb_id: {filtered_data.get('tmdb_id')}")
        print(f"  ✅ Final main_cast: {filtered_data.get('main_cast')}")
        print(f"  ✅ Final tmdb_rating: {filtered_data.get('tmdb_rating')}")
        print(f"  ✅ Final popularity_score: {filtered_data.get('popularity_score')}")
        
        return filtered_data

    def sync_movies_to_database(self, movie_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Sync multiple movies to the database with detailed error logging.
        """
        from apps.movies.models import Movie, Genre
        
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'genres_processed': 0
        }
        
        self.logger.info(f"Starting database sync for {len(movie_data_list)} movies")
        
        for i, movie_data in enumerate(movie_data_list):
            try:
                # Get the movie title for debugging - handle both data structures
                movie_title = movie_data.get('title', movie_data.get('tmdb_data', {}).get('title', f'Movie #{i}'))
                print(f"🎬 Processing movie {i+1}/{len(movie_data_list)}: {movie_title}")
                
                with transaction.atomic():
                    # Prepare database data
                    db_data = self.prepare_movie_for_database(movie_data)
                    print(f"  📋 DB data keys: {list(db_data.keys())}")
                    
                    if not db_data.get('tmdb_id'):
                        print(f"  ❌ No TMDB ID for movie: {movie_title}")
                        stats['errors'] += 1
                        continue
                    
                    print(f"  🔍 TMDB ID: {db_data.get('tmdb_id')}")
                    print(f"  🔍 Title: {db_data.get('title')}")
                    print(f"  🔍 Release date: {db_data.get('release_date')}")
                    print(f"  🔍 Rating: {db_data.get('tmdb_rating')}")
                    
                    # Try to create the movie
                    try:
                        movie, created = Movie.objects.update_or_create(
                            tmdb_id=db_data['tmdb_id'],
                            defaults=db_data
                        )
                        print(f"  ✅ {'Created' if created else 'Updated'} movie: {movie.title}")
                        
                    except Exception as db_error:
                        print(f"  ❌ Database error for {movie_title}: {db_error}")
                        print(f"  📊 DB data that failed: {db_data}")
                        stats['errors'] += 1
                        continue
                    
                    # ✅ FIXED: Handle genre relationships more flexibly
                    genre_ids = []
                    
                    # Try to get genre_ids from different locations
                    if 'genre_ids' in movie_data:
                        genre_ids = movie_data['genre_ids']
                    elif 'tmdb_data' in movie_data:
                        tmdb_data = movie_data['tmdb_data']
                        if 'genre_ids' in tmdb_data:
                            genre_ids = tmdb_data['genre_ids']
                        elif 'genres' in tmdb_data and tmdb_data['genres']:
                            genre_ids = [g['id'] for g in tmdb_data['genres'] if 'id' in g]
                    elif 'genres' in movie_data and movie_data['genres']:
                        # Handle direct genres array
                        genre_ids = [g['id'] for g in movie_data['genres'] if 'id' in g]
                    
                    print(f"  🎭 Genre IDs: {genre_ids}")
                    
                    if genre_ids:
                        genres = Genre.objects.filter(tmdb_id__in=genre_ids)
                        movie.genres.set(genres)
                        stats['genres_processed'] += len(genres)
                        print(f"  ✅ Set {len(genres)} genres")
                    
                    if created:
                        stats['created'] += 1
                    else:
                        stats['updated'] += 1
                        
            except Exception as e:
                movie_title = movie_data.get('title', movie_data.get('tmdb_data', {}).get('title', f'Movie #{i}'))
                print(f"❌ FAILED to sync movie {movie_title}: {e}")
                import traceback
                traceback.print_exc()
                stats['errors'] += 1
                continue
        
        print(f"\n📊 Final sync stats: {stats}")
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
                     popular_pages: int = 0, 
                     top_rated_pages: int = 0,
                     trending_pages: int = 0,
                     sync_genres: bool = True,
                     omdb_enrichment: bool = False) -> Dict[str, Any]:
        """
        Seed the database with movies from APIs.
        
        Args:
            popular_pages: Number of popular movie pages to fetch
            top_rated_pages: Number of top-rated movie pages to fetch
            trending_pages: Number of trending movie pages to fetch (not used in current implementation)
            sync_genres: Whether to sync genres first
            omdb_enrichment: Whether to enrich with OMDB data
            
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
            
            all_movies = []
            
            # Get popular movies
            if popular_pages > 0:
                if omdb_enrichment:
                    popular_movies = self.get_popular_movies_enriched(popular_pages)
                else:
                    # Get raw TMDB data without OMDB enrichment
                    popular_movies = self.tmdb.get_movies_by_pages('popular_movies', popular_pages)
                all_movies.extend(popular_movies)
                self.logger.info(f"Retrieved {len(popular_movies)} popular movies")
            
            # Get top-rated movies
            if top_rated_pages > 0:
                if omdb_enrichment:
                    top_rated_movies = self.get_top_rated_movies_enriched(top_rated_pages)
                else:
                    # Get raw TMDB data without OMDB enrichment
                    top_rated_movies = self.tmdb.get_movies_by_pages('top_rated_movies', top_rated_pages)
                all_movies.extend(top_rated_movies)
                self.logger.info(f"Retrieved {len(top_rated_movies)} top-rated movies")
            
            # Sync all movies to database
            if all_movies:
                movie_stats = self.sync_movies_to_database(all_movies)
                total_stats.update({
                    'movies_created': movie_stats['created'],
                    'movies_updated': movie_stats['updated'],
                    'errors': movie_stats['errors']
                })
            else:
                self.logger.warning("No movies to sync - check your parameters")
            
            total_stats['end_time'] = timezone.now()
            
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