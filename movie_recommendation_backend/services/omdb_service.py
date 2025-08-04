"""
OMDB API Service - Built using BaseAPIService

This service handles interactions with the Open Movie Database (OMDB) API
to get additional movie ratings and metadata.

OMDB API Documentation: http://www.omdbapi.com/
Rate Limits: 1000 requests per day (free tier)

"""

import logging
import time
from typing import Dict, List, Optional, Any, Union

from django.conf import settings
from django.utils import timezone

from .base_api_service import BaseAPIService, APIServiceError

logger = logging.getLogger(__name__)


# OMDB SERVICE IMPLEMENTATION

class OMDBService(BaseAPIService):
    """
    Service for interacting with the Open Movie Database (OMDB) API.
    
    Features:
    - Inherits rate limiting, error handling, and caching from BaseAPIService
    - OMDB-specific data retrieval and transformation
    - Multiple search methods (by title, IMDb ID, etc.)
    - Ratings aggregation from multiple sources
    """
    
    # REQUIRED ABSTRACT PROPERTIES
    
    @property
    def base_url(self) -> str:
        """OMDB API base URL."""
        return settings.OMDB_BASE_URL
    
    @property
    def api_key(self) -> str:
        """OMDB API key."""
        return settings.OMDB_API_KEY
    
    @property
    def rate_limit_delay(self) -> float:
        """OMDB rate limit: Conservative 1 request per second."""
        return 1.0
    
    @property
    def requests_per_day(self) -> int:
        """OMDB daily request limit (free tier)."""
        return 1000
    
    # OMDB-SPECIFIC CONFIGURATION
    @property
    def default_timeout(self) -> int:
        """OMDB can be slower, increase timeout."""
        return 45
    
    @property
    def cache_timeout_default(self) -> int:
        """Cache OMDB data longer since it updates less frequently."""
        return 86400  # 24 hours
    
    # AUTHENTICATION OVERRIDE
    
    def _add_authentication(self, params: Dict = None, headers: Dict = None) -> tuple:
        """
        OMDB uses 'apikey' parameter instead of 'api_key'.
        Override the base class authentication method.
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        
        # OMDB uses 'apikey' instead of 'api_key'
        params['apikey'] = self.api_key
        
        return params, headers

    # HEALTH CHECK
    
    def health_check(self) -> Dict[str, Any]:
        """Perform OMDB API health check."""
        try:
            start_time = time.time()
            # Simple search to test connectivity
            test_result = self.search_by_title("Inception", year=2010, plot='short')
            response_time = time.time() - start_time
            
            return {
                'service': 'OMDBService',
                'status': 'healthy',
                'response_time': round(response_time, 3),
                'circuit_breaker_state': self.circuit_breaker.state.value,
                'api_responsive': bool(test_result),
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'service': 'OMDBService',
                'status': 'unhealthy',
                'error': str(e),
                'circuit_breaker_state': self.circuit_breaker.state.value,
                'timestamp': timezone.now().isoformat()
            }
    # CORE SEARCH METHODS    
    def search_by_title(self, 
                       title: str, 
                       year: Optional[int] = None,
                       plot: str = 'short',
                       movie_type: str = 'movie') -> Dict[str, Any]:
        """
        Search for a movie by title.
        
        Args:
            title: Movie title
            year: Release year (optional)
            plot: Plot length ('short' or 'full')
            movie_type: Type ('movie', 'series', 'episode')
            
        Returns:
            Movie data from OMDB
        """
        cache_key = self._generate_cache_key(
            'search_title', 
            title=title, 
            year=year,
            plot=plot,
            type=movie_type
        )
        
        def _fetch_by_title():
            self.logger.info(f"Searching OMDB for title: '{title}' ({year})")
            
            params = {
                't': title,
                'plot': plot,
                'type': movie_type
            }
            
            if year:
                params['y'] = str(year)
            
            return self._make_request('/', params=params)
        
        return self.get_cached_or_fetch(cache_key, _fetch_by_title)
    
    def search_by_imdb_id(self, imdb_id: str, plot: str = 'short') -> Dict[str, Any]:
        """
        Search for a movie by IMDb ID.
        
        Args:
            imdb_id: IMDb ID (e.g., 'tt0111161')
            plot: Plot length ('short' or 'full')
            
        Returns:
            Movie data from OMDB
        """
        cache_key = self._generate_cache_key('search_imdb', imdb_id=imdb_id, plot=plot)
        
        def _fetch_by_imdb():
            self.logger.info(f"Searching OMDB for IMDb ID: {imdb_id}")
            
            params = {
                'i': imdb_id,
                'plot': plot
            }
            
            return self._make_request('/', params=params)
        
        return self.get_cached_or_fetch(cache_key, _fetch_by_imdb)
    
    def search_movies(self, 
                     query: str, 
                     year: Optional[int] = None,
                     page: int = 1) -> Dict[str, Any]:
        """
        Search for movies (returns multiple results).
        
        Args:
            query: Search query
            year: Release year (optional)
            page: Page number
            
        Returns:
            Search results from OMDB
        """
        self.logger.info(f"Searching OMDB for query: '{query}' (page {page})")
        
        params = {
            's': query,
            'type': 'movie',
            'page': str(page)
        }
        
        if year:
            params['y'] = str(year)
        
        return self._make_request('/', params=params)
    
    # CONVENIENCE METHODS
    
    def get_movie_by_tmdb_data(self, tmdb_movie: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get OMDB data for a movie using TMDB movie data.
        
        Args:
            tmdb_movie: Movie data from TMDB
            
        Returns:
            OMDB movie data or None
        """
        # Try IMDb ID first (most accurate)
        imdb_id = tmdb_movie.get('imdb_id')
        if imdb_id:
            try:
                omdb_data = self.search_by_imdb_id(imdb_id)
                if omdb_data and omdb_data.get('Response') == 'True':
                    return omdb_data
            except Exception as e:
                self.logger.warning(f"Failed to fetch OMDB data by IMDb ID {imdb_id}: {e}")
        
        # Fallback to title and year search
        title = tmdb_movie.get('title')
        release_date = tmdb_movie.get('release_date')
        
        if title:
            try:
                year = None
                if release_date:
                    if isinstance(release_date, str):
                        year = int(release_date[:4])
                    else:
                        year = release_date.year
                
                omdb_data = self.search_by_title(title, year=year)
                if omdb_data and omdb_data.get('Response') == 'True':
                    return omdb_data
                    
            except Exception as e:
                self.logger.warning(f"Failed to fetch OMDB data by title '{title}': {e}")
        
        return None
    
    def get_multiple_movies_by_imdb_ids(self, imdb_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get OMDB data for multiple movies by IMDb IDs.
        
        Args:
            imdb_ids: List of IMDb IDs
            
        Returns:
            Dictionary mapping IMDb ID to OMDB data
        """
        results = {}
        
        for imdb_id in imdb_ids:
            try:
                omdb_data = self.search_by_imdb_id(imdb_id)
                if omdb_data and omdb_data.get('Response') == 'True':
                    results[imdb_id] = omdb_data
                
                # Respect rate limits
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                self.logger.error(f"Failed to fetch OMDB data for {imdb_id}: {e}")
                continue
        
        self.logger.info(f"Fetched OMDB data for {len(results)} out of {len(imdb_ids)} movies")
        return results
    
    # DATA EXTRACTION UTILITIES
    
    def extract_ratings(self, omdb_data: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """
        Extract ratings from OMDB data.
        
        Args:
            omdb_data: Movie data from OMDB
            
        Returns:
            Dictionary with rating sources and values
        """
        ratings = {
            'imdb_rating': None,
            'rotten_tomatoes_rating': None,
            'metacritic_rating': None
        }
        
        # IMDb rating (direct field)
        imdb_rating = omdb_data.get('imdbRating')
        if imdb_rating and imdb_rating != 'N/A':
            try:
                ratings['imdb_rating'] = float(imdb_rating)
            except ValueError:
                pass
        
        # Ratings array
        ratings_array = omdb_data.get('Ratings', [])
        
        for rating in ratings_array:
            source = rating.get('Source', '').lower()
            value = rating.get('Value', '')
            
            if 'rotten tomatoes' in source and '%' in value:
                try:
                    # Convert percentage to 0-10 scale
                    percentage = int(value.replace('%', ''))
                    ratings['rotten_tomatoes_rating'] = percentage / 10.0
                except ValueError:
                    pass
            
            elif 'metacritic' in source and '/' in value:
                try:
                    # Convert X/100 to 0-10 scale
                    score = int(value.split('/')[0])
                    ratings['metacritic_rating'] = score / 10.0
                except ValueError:
                    pass
        
        return ratings
    
    def extract_additional_info(self, omdb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract additional information from OMDB data.
        
        Args:
            omdb_data: Movie data from OMDB
            
        Returns:
            Dictionary with additional movie information
        """
        return {
            'rated': omdb_data.get('Rated'),
            'released': omdb_data.get('Released'),
            'runtime': omdb_data.get('Runtime'),
            'director': omdb_data.get('Director'),
            'writer': omdb_data.get('Writer'),
            'actors': omdb_data.get('Actors'),
            'plot': omdb_data.get('Plot'),
            'language': omdb_data.get('Language'),
            'country': omdb_data.get('Country'),
            'awards': omdb_data.get('Awards'),
            'box_office': omdb_data.get('BoxOffice'),
            'production': omdb_data.get('Production'),
            'website': omdb_data.get('Website'),
            'imdb_votes': omdb_data.get('imdbVotes'),
            'dvd': omdb_data.get('DVD'),
        }
    
    def is_valid_response(self, omdb_data: Dict[str, Any]) -> bool:
        """
        Check if OMDB response is valid and contains movie data.
        
        Args:
            omdb_data: Response from OMDB API
            
        Returns:
            True if response contains valid movie data
        """
        return (
            omdb_data and 
            omdb_data.get('Response') == 'True' and 
            omdb_data.get('Title') is not None
        )
    
    def get_error_message(self, omdb_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract error message from OMDB response.
        
        Args:
            omdb_data: Response from OMDB API
            
        Returns:
            Error message or None
        """
        if omdb_data and omdb_data.get('Response') == 'False':
            return omdb_data.get('Error', 'Unknown OMDB error')
        return None
    
    # BULK OPERATIONS
    
    def enrich_tmdb_movies(self, tmdb_movies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich TMDB movie data with OMDB ratings and information.
        
        Args:
            tmdb_movies: List of movies from TMDB
            
        Returns:
            List of movies enriched with OMDB data
        """
        enriched_movies = []
        
        for tmdb_movie in tmdb_movies:
            try:
                # Get OMDB data
                omdb_data = self.get_movie_by_tmdb_data(tmdb_movie)
                
                # Create enriched movie object
                enriched_movie = tmdb_movie.copy()
                
                if omdb_data and self.is_valid_response(omdb_data):
                    # Add OMDB ratings
                    ratings = self.extract_ratings(omdb_data)
                    enriched_movie.update({
                        'omdb_ratings': ratings,
                        'omdb_data': self.extract_additional_info(omdb_data)
                    })
                    
                    self.logger.debug(f"Enriched movie: {tmdb_movie.get('title')}")
                else:
                    error_msg = self.get_error_message(omdb_data)
                    self.logger.warning(f"No OMDB data for {tmdb_movie.get('title')}: {error_msg}")
                    
                    enriched_movie.update({
                        'omdb_ratings': {},
                        'omdb_data': {}
                    })
                
                enriched_movies.append(enriched_movie)
                
                # Respect rate limits
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                self.logger.error(f"Failed to enrich movie {tmdb_movie.get('title')}: {e}")
                # Add movie without OMDB data
                enriched_movie = tmdb_movie.copy()
                enriched_movie.update({
                    'omdb_ratings': {},
                    'omdb_data': {}
                })
                enriched_movies.append(enriched_movie)
        
        success_count = sum(1 for m in enriched_movies if m.get('omdb_ratings'))
        self.logger.info(f"Successfully enriched {success_count} out of {len(tmdb_movies)} movies")
        
        return enriched_movies
    
# CONVENIENCE FUNCTIONS

def get_omdb_service() -> OMDBService:
    """
    Get a configured OMDB service instance.
    
    Returns:
        OMDBService instance
    """
    return OMDBService()
