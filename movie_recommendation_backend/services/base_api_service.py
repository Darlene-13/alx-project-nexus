"""
This is the base API service for our Movie Recommendation Backend.
Our service handles the interaction with external API like TMDB and OMDB.
It includes different methods like handling API requests, error handling, caching amongst others.
Our two main APIs will be able to inherit from this base service.
"""

import requests
import logging
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

# Custom exception for api errors.
class APIServiceError(Exception):
    """ Base exception for the API service errors."""
    def __init__(self, message:str, status_code: Optional[int]= None, response_data: Optional[Dict]=None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)   # Calling the parent class constructor

class RateLimitExceededError(APIServiceError):
    """ Exception raised when the API rate limit is exceeded."""
    pass

class AuthenticationError(APIServiceError):
    """ Exception raised for authentication errors."""
    pass

class APITimeoutError(APIServiceError):
    """ Exception raised for API timeout errors."""
    pass

class APIServerError(APIServiceError):
    """ Exception raised for server errors."""
    pass


# Circuit breaker implementation
class CircuitState(Enum):
    CLOSED = "closed" # Normal operation
    OPEN = "open" # Circuit is open
    HALF_OPEN = "half_open" # Circuit is half open

class CircuitBreaker:
    """
    A simple circuit breaker implementation to prevent overwhelming the API with requests
    when it is known to be failing.
    """
    def __init__(self, failure_threshold: int=5, recovery_timeout: int=60, expected_exception: Exception = APIServiceError):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception


        self.failure_count = 0
        self.last_failure-time = None
        self.state - CircuitState.CLOSED


        def call(self, func, *args, **kwargs):
            """
            Execute the function with the circuit breaker logic.
            """
            if self.state == CircuitState.OPEN:
                if self.last_failure_time and (timezone.now() - self.last_failure_time).total_seconds() < self.recovery_timeout:
                    raise RateLimitExceededError("Circuit is open, requests are not allowed at this time.")
                else:
                    self.state = CircuitState.HALF_OPEN

            try:
                result = func(*args, **kwargs)
                self.reset()
                return result
            except self.expected_exception as e:
                self.record_failure(e)
                raise e
            
        def _should_attempt_reset(self) -> bool:
            """
            Check if the circuit breaker should attempt to reset.
            """
            if self.state == CircuitState.HALF_OPEN:
                if self.last_failure_time and (timezone.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout:
                    return True
            return False
        
        def _on_sucess(self):
            """
            Reset the circuit breaker state on success.
            """
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            self.last_failure_time = None
        def on_failure(self):
            if self.failure_count >= self.failure_threshold:
                logging.warning("Circuit breaker reset after successful request.")
                self.state = CircuitState.OPEN
# BASE API SERVICE CLASS
class BaseAPIService(ABC):
    """
    Base class for the API services.
    Provides a common functionality for all our API services.
    - Rate limiting
    - Error handling
    - Circuit breaking pattern
    - Request /response logging
    - Caching integration
    - Authentication handling
    """
    def __init__(self):
        """ Initialize the base API Service."""
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.last_request_time = 0

        # Initialize the circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold = self.failure_threshold,
            recovery_timeout = self.recovery_timeout
        )

        # Set up session with optimizations
        self._setup_session()

        # Validate configuration
        self._validate_config()
        self.logger.info("Base API Service initialized successfully.")

    # Properties to be implemented by subclasses
    @property
    @abstractmethod
    def base_url(self) -> str:
        """ Base URL for the API service. Must be implemented by subclasses."""
        pass

    @property
    @abstractmethod
    def api_key(self) -> str:
        """ API key for authentication. Must be implemented by subclasses."""
        pass

    @property
    @abstractmethod
    def rate_limit_delay(self) -> float:
        """ Rate limit delay in seconds. Must be implemented by subclasses."""
        pass

    @property
    @abstractmethod
    def requests_per_day(self) -> int:
        """ Number of requests allowed per day. Must be implemented by subclasses."""
        pass

    # Configure Properties --This is where we set the properties for the API service
    @property
    def default_timeout(self) -> int:
        return 30
    
    @property
    def max_retries(self) -> int:
        return 3
    
    @property
    def failure_threshold(self) -> int:
        return 5
    
    @property
    def cache_timeout_default(self) -> int:
        return 3600  # 1 hour
    
    # Session setup and configuration

    def _setup_session(self):
        """
        configure requests sessions with optimizations.
        """
        retry_strategy = Retry(
            total=0,
            connect=2,
            backoff_factor=1,
        )

        # Confugure adapter with connection pooling 
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            "User-Agent": "MovieRecommendationBackend/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        })
    
    def _validate_config(self):
        """
        Validate the configuration settings for the API service.
        """

        if not self.base_url:
            raise ValueError("Base URL must be set for the API service.")
        if not self.api_key:
            raise ValueError("API key must be set for the API service.")
        if self.rate_limit_delay <= 0:
            raise ValueError("Rate limit delay must be a positive number.")
        if self.requests_per_day <= 0:
            raise ValueError("Requests per day must be a positive integer.")
        
    def _add_authentication(self, params: Dict [str, Any], headers: Dict=None) -> tuple:
        """
        Add authentication parameters to the request.
        Override this method for different auth methods.
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        #Default: API key in query parameters
        params['api_key'] = self.api_key

        return params, headers
    
    # RATE LIMITING AND THROTTLING
    def __enforce_rate_limit(self):
        """
        Enforce rate limiting by checking the time since the last request.
        """
        current_time = time.time()
        elapsed_time = current_time - self.last_request_time

        if elapsed_time < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed_time
            self.logger.info(f"Rate limit enforced. Sleeping for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)

        self.last_request_time = current_time

    # Core request handling logic
    def _make_request(self,
                      endpoint: str,
                      params: Optional[Dict] = None,
                      headers: Optional[Dict] = None,
                      timeout: Optional[int] = None,
                      method: str = 'GET',
                      data: Optional[Dict] = None) -> Dict [ str, Any]:
        """
        Make the API request with error handling, rate limiting, and caching.
        It returns the JSON response data.
        """

        return self.circuit_breaker.call(self._make_request_internal, endpoint, params, headers, timeout, method, data)

    def _make_request_internal(self, endpoint, params, headers, timeout, method, data):
        """
        Internal request method called through the circuit breaker.
        """

        self._enforce_rate_limit()

        # Build the full URL
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        # Add authentication parameters
        params, headers = self._add_authentication(params, headers)

        # Set default timeout if not provided
        timeout = timeout or self.default_timeout

        # Log request details
        self.logger.debug(f"Making {method} request to {url} with params: {params} and headers: {headers}")

        # Retry logic for API errors
        for attempt in range(self.max_retries):
            try:
                # Make the request
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                    json=data if method != 'GET' else None
                )

                self.last_request_time = time.time() # Update last request time 

                return self._handle_response(response, endpoint, attempt)
            except requests.exceptions.Timeout as e:
                last_exception = APITimeoutError(f" Request timeout: {e}")
                self.logger.warning(f" Request timeout (attempt {attempt + 1}): {endpoint}")
            except requests.exceptions.ConnectionError as e:
                last_exception = APIServiceError(f" Connection error: {e}")
                self.logger.warning(f" Connection error (attempt {attempt + 1}): {endpoint}")
            except requests.exceptions.RequestException as e:
                last_exception = APIServiceError(f" Request error: {e}")
                self.logger.warning(f" Request error (attempt {attempt + 1}): {endpoint}")

            # Exponential backoff between retries
            if attempt < self.max_retries - 1:
                sleep_time = 2 ** attempt
                self.logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

            # All retries failed, raise the last exception
            raise last_exception or APIServiceError(" Request failed after all the retries.")


        def _handle_response(self, response, endpoint: str, attempt: int) -> Dict[str, Any]:
            """
            Handle HTTP response and convert to appropriate exceptions.
            
            Args:
                response: requests.Response object
                endpoint: API endpoint for logging
                attempt: Current attempt number
                
            Returns:
                Parsed JSON response
                
            Raises:
                Various APIServiceError subclasses
            """
        status_code = response.status_code
        
        # Success
        if 200 <= status_code < 300:
            try:
                data = response.json()
                self.logger.debug(f"Request successful: {endpoint}")
                return data
            except json.JSONDecodeError:
                raise APIServiceError(f"Invalid JSON response: {response.text[:200]}")
        
        # Client errors
        elif status_code == 401:
            raise AuthenticationError("Invalid API credentials")
        
        elif status_code == 403:
            raise AuthenticationError("API access forbidden")
        
        elif status_code == 404:
            self.logger.warning(f"Resource not found: {endpoint}")
            return {}  # Return empty dict for missing resources
        
        elif status_code == 429:
            # Rate limit exceeded - should be retried
            retry_after = response.headers.get('Retry-After', '10')
            try:
                wait_time = int(retry_after)
            except ValueError:
                wait_time = 10
                
            self.logger.warning(f"Rate limit exceeded. Waiting {wait_time}s...")
            time.sleep(wait_time)
            raise RateLimitExceededError(f"Rate limit exceeded, waited {wait_time}s")
        
        elif 400 <= status_code < 500:
            raise APIServiceError(f"Client error {status_code}: {response.text[:200]}")
        
        # Server errors
        elif 500 <= status_code < 600:
            raise APIServerError(f"Server error {status_code}: {response.text[:200]}")
        
        else:
            raise APIServiceError(f"Unexpected status code {status_code}: {response.text[:200]}")

    # CACHING UTILITIES
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate consistent cache key from parameters."""
        import hashlib
        
        # Create deterministic key from parameters
        key_data = json.dumps(kwargs, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        
        service_name = self.__class__.__name__.lower().replace('service', '')
        return f"{service_name}_{prefix}_{key_hash}"
    
    def get_cached_or_fetch(self, 
                           cache_key: str, 
                           fetch_function,
                           cache_timeout: Optional[int] = None,
                           *args, **kwargs) -> Any:
        """
        Get data from cache or fetch from API if not cached.     
        Returns: Cached or fetched data
        """
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            self.logger.debug(f"Cache hit: {cache_key}")
            return cached_data
        
        # Cache miss - fetch from API
        self.logger.debug(f"Cache miss: {cache_key}")
        data = fetch_function(*args, **kwargs)
        
        # Cache the result if it's not empty
        if data:
            timeout = cache_timeout or self.cache_timeout_default
            cache.set(cache_key, data, timeout)
            self.logger.debug(f"Cached data for {timeout}s: {cache_key}")
        
        return data
    # UTILITY METHODS  
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the API service.
        Override this method in subclasses with a simple API call.
        
        Returns:
            Health check results
        """
        try:
            # This should be overridden by subclasses with actual health check
            start_time = time.time()
            # Make a simple API call - subclasses should implement this
            response_time = time.time() - start_time
            
            return {
                'service': self.__class__.__name__,
                'status': 'healthy',
                'response_time': round(response_time, 3),
                'circuit_breaker_state': self.circuit_breaker.state.value,
                'last_request_time': self.last_request_time,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'service': self.__class__.__name__,
                'status': 'unhealthy',
                'error': str(e),
                'circuit_breaker_state': self.circuit_breaker.state.value,
                'timestamp': timezone.now().isoformat()
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        # This would typically integrate with your metrics system
        return {
            'service': self.__class__.__name__,
            'circuit_breaker_state': self.circuit_breaker.state.value,
            'failure_count': self.circuit_breaker.failure_count,
            'last_failure_time': self.circuit_breaker.last_failure_time,
            'last_request_time': self.last_request_time,
        }
    
    def __str__(self):
        """String representation of the service."""
        return f"{self.__class__.__name__}(base_url={self.base_url})"
    
    def __repr__(self):
        """Developer representation of the service."""
        return (f"{self.__class__.__name__}("
                f"base_url={self.base_url}, "
                f"rate_limit={self.rate_limit_delay}s)")
# UTILITY FUNCTIONS
def get_api_service_health() -> Dict[str, Any]:
    """
    Get health status of all registered API services.
    This would be used in Django health check endpoints.
    """
    # This is a placeholder - in real implementation, it would good to maintain
    # a registry of all active API services
    return {
        'timestamp': timezone.now().isoformat(),
        'services': [],  # Would be populated with actual services
        'overall_status': 'healthy'
    }                
    


