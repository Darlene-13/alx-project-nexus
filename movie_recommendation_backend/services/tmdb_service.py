"""
TMDB API Service 

This service handles the interactions with the The Movie Database (TMDB) API.
It includes methods for fetching movie details, searching for movies, and handling API rate limits.
The TMDB API documentation can be found at https://developers.themoviedb.org/3/getting-started/introduction.

"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, time

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .base_api_service import BaseAPIService, APIServiceError

logger = logging.getLogger(__name__)

# TMDB SERVICE IMPLEMENTATION

class TMDBService(BaseAPIService):
    """
    Service for interacting with The Movie Database (TMDB) API.
    
    Features:
    - Inherits rate limiting, error handling, and caching from BaseAPIService
    - TMDB-specific endpoints and data transformation
    - Image URL generation
    - Cast and crew data extraction
    """
    
    @property
    def base_url(self) -> str:
        """TMDB API base URL."""
        return settings.TMDB_BASE_URL
    
    @property
    def api_key(self) -> str:
        """TMDB API key."""
        return settings.TMDB_API_KEY
    
    @property
    def rate_limit_delay(self) -> float:
        """TMDB rate limit: 40 requests per 10 seconds = 0.25s delay."""
        return 0.25
    
    @property
    def requests_per_day(self) -> int:
        """TMDB daily request limit (very high)."""
        return 1000000  # Essentially unlimited for most use cases
    
    # TMDB-SPECIFIC CONFIGURATION
    
    @property
    def image_base_url(self) -> str:
        """TMDB image base URL."""
        return "https://image.tmdb.org/t/p"
    
    @property
    def endpoints(self) -> Dict[str, str]:
        """TMDB API endpoints."""
        return {
            'configuration': '/configuration',
            'genres': '/genre/movie/list',
            'popular_movies': '/movie/popular',
            'top_rated_movies': '/movie/top_rated',
            'trending_movies': '/trending/movie/day',
            'movie_details': '/movie/{movie_id}',
            'movie_credits': '/movie/{movie_id}/credits',
            'search_movies': '/search/movie',
            'discover_movies': '/discover/movie',
        }
    
    # HEALTH CHECK
    
    def health_check(self) -> Dict[str, Any]:
        """Perform TMDB API health check."""
        try:
            start_time = time.time()
            # Simple API call to check connectivity
            config = self.get_configuration()
            response_time = time.time() - start_time
            
            return {
                'service': 'TMDBService',
                'status': 'healthy',
                'response_time': round(response_time, 3),
                'circuit_breaker_state': self.circuit_breaker.state.value,
                'api_responsive': bool(config),
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'service': 'TMDBService',
                'status': 'unhealthy',
                'error': str(e),
                'circuit_breaker_state': self.circuit_breaker.state.value,
                'timestamp': timezone.now().isoformat()
            }
    
    # CONFIGURATION AND SETUP
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get TMDB API configuration (includes image base URLs).
        Cached for 24 hours since configuration rarely changes.
        
        Returns:
            Configuration data including image base URLs
        """
        cache_key = self._generate_cache_key('configuration')
        
        def _fetch_config():
            self.logger.info("Fetching TMDB configuration")
            return self._make_request(self.endpoints['configuration'])
        
        return self.get_cached_or_fetch(
            cache_key, 
            _fetch_config,
            cache_timeout=86400  # 24 hours
        )
    
    # GENRE METHODS
    
    def get_genres(self) -> List[Dict[str, Any]]:
        """
        Fetch all movie genres from TMDB.
        Cached for 24 hours since genres rarely change.
        
        Returns:
            List of genre dictionaries with id, name
        """
        cache_key = self._generate_cache_key('genres')
        
        def _fetch_genres():
            self.logger.info("Fetching movie genres from TMDB")
            response = self._make_request(self.endpoints['genres'])
            return response.get('genres', [])
        
        return self.get_cached_or_fetch(
            cache_key, 
            _fetch_genres,
            cache_timeout=86400  # 24 hours
        )
    # MOVIE DISCOVERY METHODS
    
    def get_popular_movies(self, page: int = 1) -> Dict[str, Any]:
        """
        Get popular movies from TMDB.
        
        Args:
            page: Page number (1-based)
            
        Returns:
            Dictionary containing results and pagination info
        """
        cache_key = self._generate_cache_key('popular_movies', page=page)
        
        def _fetch_popular():
            self.logger.info(f"Fetching popular movies page {page} from TMDB")
            return self._make_request(
                self.endpoints['popular_movies'],
                params={'page': page}
            )
        
        return self.get_cached_or_fetch(
            cache_key,
            _fetch_popular,
            cache_timeout=3600  # 1 hour
        )
    
    def get_top_rated_movies(self, page: int = 1) -> Dict[str, Any]:
        """
        Get top-rated movies from TMDB.
        
        Args:
            page: Page number (1-based)
            
        Returns:
            Dictionary containing results and pagination info
        """
        cache_key = self._generate_cache_key('top_rated_movies', page=page)
        
        def _fetch_top_rated():
            self.logger.info(f"Fetching top-rated movies page {page} from TMDB")
            return self._make_request(
                self.endpoints['top_rated_movies'],
                params={'page': page}
            )
        
        return self.get_cached_or_fetch(
            cache_key,
            _fetch_top_rated,
            cache_timeout=3600  # 1 hour
        )
    
    def get_trending_movies(self, time_window: str = 'day') -> Dict[str, Any]:
        """
        Get trending movies from TMDB.
        
        Args:
            time_window: 'day' or 'week'
            
        Returns:
            Dictionary containing trending movies
        """
        cache_key = self._generate_cache_key('trending_movies', time_window=time_window)
        
        def _fetch_trending():
            self.logger.info(f"Fetching trending movies ({time_window}) from TMDB")
            endpoint = f'/trending/movie/{time_window}'
            return self._make_request(endpoint)
        
        return self.get_cached_or_fetch(
            cache_key,
            _fetch_trending,
            cache_timeout=1800  # 30 minutes
        )
    
    def discover_movies(self, **filters) -> Dict[str, Any]:
        """
        Discover movies with filters.
        
        Args:
            **filters: Filter parameters (genre, year, rating, etc.)
            
        Returns:
            Dictionary containing discovered movies
        """
        cache_key = self._generate_cache_key('discover_movies', **filters)
        
        def _fetch_discovered():
            self.logger.info(f"Discovering movies with filters: {filters}")
            return self._make_request(
                self.endpoints['discover_movies'],
                params=filters
            )
        
        return self.get_cached_or_fetch(
            cache_key,
            _fetch_discovered,
            cache_timeout=3600  # 1 hour
        )
    
    def search_movies(self, query: str, page: int = 1) -> Dict[str, Any]:
        """
        Search for movies by title.
        
        Args:
            query: Search query
            page: Page number
            
        Returns:
            Dictionary containing search results
        """
        # Don't cache search results as they're user-specific
        self.logger.info(f"Searching movies for: '{query}' (page {page})")
        return self._make_request(
            self.endpoints['search_movies'],
            params={'query': query, 'page': page}
        )

    # DETAILED MOVIE INFORMATION
    
    def get_movie_details(self, tmdb_id: int) -> Dict[str, Any]:
        """
        Get detailed information for a specific movie.
        
        Args:
            tmdb_id: TMDB movie ID
            
        Returns:
            Detailed movie information
        """
        cache_key = self._generate_cache_key('movie_details', tmdb_id=tmdb_id)
        
        def _fetch_details():
            self.logger.debug(f"Fetching movie details for TMDB ID: {tmdb_id}")
            endpoint = self.endpoints['movie_details'].format(movie_id=tmdb_id)
            return self._make_request(endpoint)
        
        return self.get_cached_or_fetch(
            cache_key,
            _fetch_details,
            cache_timeout=86400  # 24 hours
        )
    
    def get_movie_credits(self, tmdb_id: int) -> Dict[str, Any]:
        """
        Get cast and crew information for a specific movie.
        
        Args:
            tmdb_id: TMDB movie ID
            
        Returns:
            Cast and crew information
        """
        cache_key = self._generate_cache_key('movie_credits', tmdb_id=tmdb_id)
        
        def _fetch_credits():
            self.logger.debug(f"Fetching movie credits for TMDB ID: {tmdb_id}")
            endpoint = self.endpoints['movie_credits'].format(movie_id=tmdb_id)
            return self._make_request(endpoint)
        
        return self.get_cached_or_fetch(
            cache_key,
            _fetch_credits,
            cache_timeout=86400  # 24 hours
        )
    # BULK OPERATIONS..
    
    def get_multiple_movies(self, movie_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get details for multiple movies efficiently.
        
        Args:
            movie_ids: List of TMDB movie IDs
            
        Returns:
            List of movie details
        """
        movies = []
        
        for tmdb_id in movie_ids:
            try:
                movie_data = self.get_movie_details(tmdb_id)
                if movie_data:
                    movies.append(movie_data)
                    
                # Small delay to respect rate limits
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to fetch movie {tmdb_id}: {e}")
                continue
        
        self.logger.info(f"Fetched {len(movies)} out of {len(movie_ids)} movies")
        return movies
    
    def get_movies_by_pages(self, endpoint_name: str, pages: int = 5) -> List[Dict[str, Any]]:
        """
        Get movies from multiple pages of a paginated endpoint.
        
        Args:
            endpoint_name: Name of endpoint ('popular_movies', 'top_rated_movies')
            pages: Number of pages to fetch
            
        Returns:
            List of all movies from all pages
        """
        all_movies = []
        
        for page in range(1, pages + 1):
            try:
                if endpoint_name == 'popular_movies':
                    response = self.get_popular_movies(page)
                elif endpoint_name == 'top_rated_movies':
                    response = self.get_top_rated_movies(page)
                else:
                    raise ValueError(f"Unknown endpoint: {endpoint_name}")
                
                movies = response.get('results', [])
                all_movies.extend(movies)
                
                self.logger.info(f"Fetched page {page}/{pages}: {len(movies)} movies")
                
                # If we get fewer than 20 movies, we've reached the end
                if len(movies) < 20:
                    break
                    
            except Exception as e:
                self.logger.error(f"Failed to fetch page {page}: {e}")
                break
        
        self.logger.info(f"Total movies fetched: {len(all_movies)}")
        return all_movies
    
    # IMAGE URL GENERATION
    def get_image_url(self, image_path: Optional[str], size: str = 'w500') -> Optional[str]:
        """
        Generate full TMDB image URL.
        
        Args:
            image_path: Relative image path from TMDB
            size: Image size (w500, w780, original, etc.)
            
        Returns:
            Full image URL or None
        """
        if not image_path:
            return None
        
        return f"{self.image_base_url}/{size}{image_path}"
    
    def get_poster_url(self, poster_path: Optional[str], size: str = 'w500') -> Optional[str]:
        """Get poster URL with default size."""
        return self.get_image_url(poster_path, size)
    
    def get_backdrop_url(self, backdrop_path: Optional[str], size: str = 'original') -> Optional[str]:
        """Get backdrop URL with default size."""
        return self.get_image_url(backdrop_path, size)

    # DATA EXTRACTION UTILITIES
    def extract_director(self, credits_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract director name from credits data.
        
        Args:
            credits_data: Credits data from TMDB
            
        Returns:
            Director name or None
        """
        crew = credits_data.get('crew', [])
        
        for person in crew:
            if person.get('job') == 'Director':
                return person.get('name')
        
        return None
    
    def extract_main_cast(self, credits_data: Dict[str, Any], limit: int = 5) -> List[str]:
        """
        Extract main cast names from credits data.
        
        Args:
            credits_data: Credits data from TMDB
            limit: Maximum number of cast members to return
            
        Returns:
            List of actor names
        """
        cast = credits_data.get('cast', [])
        
        # Sort by order (billing order) and take the first 'limit' actors
        sorted_cast = sorted(cast, key=lambda x: x.get('order', 999))
        main_cast = [person.get('name') for person in sorted_cast[:limit]]
        
        return [name for name in main_cast if name]  # Filter out None values
    
    def extract_genre_names(self, movie_data: Dict[str, Any]) -> List[str]:
        """
        Extract genre names from movie data.
        
        Args:
            movie_data: Movie data from TMDB
            
        Returns:
            List of genre names
        """
        genres = movie_data.get('genres', [])
        return [genre.get('name') for genre in genres if genre.get('name')]
    
    def extract_production_companies(self, movie_data: Dict[str, Any]) -> List[str]:
        """
        Extract production company names from movie data.
        
        Args:
            movie_data: Movie data from TMDB
            
        Returns:
            List of production company names
        """
        companies = movie_data.get('production_companies', [])
        return [company.get('name') for company in companies if company.get('name')]

# CONVENIENCE FUNCTIONS

def get_tmdb_service() -> TMDBService:
    """
    Get a configured TMDB service instance.
    
    Returns:
        TMDBService instance
    """
    return TMDBService()
