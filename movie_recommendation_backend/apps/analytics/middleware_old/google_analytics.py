import os
import uuid
import time
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from urllib.parse import urlencode
from threading import Thread
from dotenv import load_dotenv
import requests

logger = logging.getLogger(__name__)

class GoogleAnalyticsMiddleware(MiddlewareMixin):
    """
    Improved Google Analytics 4 Measurement Protocol middleware
    with better error handling, caching, and async processing
    Uses environment variables for configuration
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Read configuration from environment variables
        self.measurement_id = os.environ.get('GA_MEASUREMENT_ID')
        self.api_secret = os.environ.get('GA_API_KEY')
        self.enabled = os.environ.get('GA_ENABLED', 'true').lower() == 'true'
        self.debug = os.environ.get('GA_DEBUG', 'false').lower() == 'true'
        self.timeout = int(os.environ.get('GA_TIMEOUT', '5'))
        
        # Build GA4 URL
        if self.measurement_id and self.api_secret:
            self.ga_url = f"https://www.google-analytics.com/mp/collect?measurement_id={self.measurement_id}&api_secret={self.api_secret}"
        else:
            self.enabled = False
            logger.warning("Google Analytics not properly configured - tracking disabled")
            logger.warning(f"Missing: GA_MEASUREMENT_ID={'✓' if self.measurement_id else '✗'}, GA_API_SECRET={'✓' if self.api_secret else '✗'}")

    def process_request(self, request):
        """Start timer and setup tracking data"""
        request._ga_start_time = time.time()
        
        # Generate or retrieve client ID
        client_id = request.COOKIES.get('ga_client_id')
        if not client_id:
            client_id = str(uuid.uuid4())
            request._ga_new_client = True
        else:
            request._ga_new_client = False
            
        request._ga_client_id = client_id
        return None

    def process_response(self, request, response):
        """Send analytics data after response is ready"""
        if not self.enabled:
            return response
            
        # Set client ID cookie if new
        if getattr(request, '_ga_new_client', False):
            response.set_cookie(
                'ga_client_id', 
                request._ga_client_id,
                max_age=63072000,  # 2 years
                httponly=True,
                secure=request.is_secure()
            )
        
        # Skip certain paths
        if self._should_skip_tracking(request):
            return response
            
        # Prepare event data
        event_data = self._prepare_event_data(request, response)
        
        if event_data:
            # Send asynchronously to avoid blocking response
            self._send_to_ga_async(event_data)
        
        return response
    
    def _should_skip_tracking(self, request):
        """Determine if request should be tracked"""
        # Get skip paths from environment (comma-separated)
        default_skip_paths = '/admin/,/static/,/media/,/favicon.ico,/health/,/silk/'
        skip_paths_str = os.environ.get('GA_SKIP_PATHS', default_skip_paths)
        skip_paths = [path.strip() for path in skip_paths_str.split(',') if path.strip()]
        
        skip_methods = ['OPTIONS', 'HEAD']
        
        return (
            request.method in skip_methods or
            any(request.path.startswith(path) for path in skip_paths) or
            'bot' in request.META.get('HTTP_USER_AGENT', '').lower()
        )
    
    def _prepare_event_data(self, request, response):
        """Prepare GA4 event data"""
        try:
            # Calculate duration
            duration_ms = int((time.time() - getattr(request, '_ga_start_time', time.time())) * 1000)
            
            # Get user ID if authenticated
            user_id = str(request.user.id) if request.user.is_authenticated else None
            
            # Safe query parameters (limit for privacy)
            max_params = int(os.environ.get('GA_MAX_QUERY_PARAMS', '5'))
            query_params = dict(list(request.GET.items())[:max_params])
            
            # Determine event name based on path
            event_name = self._get_event_name(request.path, request.method)
            
            # Prepare event parameters
            event_params = {
                'page_location': request.build_absolute_uri(),
                'page_title': f"{request.method} {request.path}",
                'method': request.method,
                'status_code': response.status_code,
                'response_time': duration_ms,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100],
            }
            
            # Add query parameters if present
            if query_params:
                event_params['query_params'] = json.dumps(query_params)
            
            # Add user-specific data
            if user_id:
                event_params['user_type'] = 'authenticated'
            else:
                event_params['user_type'] = 'anonymous'
            
            # Add custom dimensions based on path
            custom_dimensions = self._get_custom_dimensions(request)
            event_params.update(custom_dimensions)
            
            # Build event data
            event_data = {
                'client_id': getattr(request, '_ga_client_id', str(uuid.uuid4())),
                'events': [{
                    'name': event_name,
                    'params': event_params
                }]
            }
            
            # Add user_id if authenticated
            if user_id:
                event_data['user_id'] = user_id
            
            return event_data
            
        except Exception as e:
            logger.error(f"Failed to prepare GA event data: {e}")
            return None
    
    def _get_event_name(self, path, method):
        """Generate appropriate event name based on path and method"""
        # API endpoints
        if path.startswith('/api/'):
            if 'recommendations' in path:
                return 'api_recommendation_request'
            elif 'movies' in path:
                return 'api_movie_request'
            elif 'auth' in path:
                return 'api_auth_request'
            else:
                return 'api_request'
        
        # Admin endpoints
        elif path.startswith('/admin/'):
            return 'admin_access'
        
        # Static/media files
        elif path.startswith(('/static/', '/media/')):
            return 'static_file_access'
        
        # Default page view
        else:
            return 'page_view'
    
    def _get_custom_dimensions(self, request):
        """Extract custom dimensions based on request"""
        dimensions = {}
        
        # Extract movie ID from path
        if '/movies/' in request.path:
            path_parts = request.path.split('/')
            try:
                movie_index = path_parts.index('movies')
                if movie_index + 1 < len(path_parts) and path_parts[movie_index + 1].isdigit():
                    dimensions['movie_id'] = path_parts[movie_index + 1]
            except (ValueError, IndexError):
                pass
        
        # Extract recommendation context
        if '/recommendations/' in request.path:
            dimensions['recommendation_context'] = True
            
        # Add device type
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'mobile' in user_agent:
            dimensions['device_type'] = 'mobile'
        elif 'tablet' in user_agent:
            dimensions['device_type'] = 'tablet'
        else:
            dimensions['device_type'] = 'desktop'
            
        return dimensions
    
    def _send_to_ga_async(self, event_data):
        """Send event data to GA4 asynchronously"""
        if self.debug:
            logger.info(f"GA4 Event: {json.dumps(event_data, indent=2)}")
            return
        
        def send_request():
            try:
                # Get user agent from environment or use default
                user_agent = os.environ.get('GA_USER_AGENT', 'MovieRec-Analytics/1.0')
                
                response = requests.post(
                    self.ga_url,
                    json=event_data,
                    timeout=self.timeout,
                    headers={'User-Agent': user_agent}
                )
                
                if response.status_code == 204:
                    logger.debug("GA4 event sent successfully")
                else:
                    logger.warning(f"GA4 event failed: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"GA4 request failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected GA4 error: {e}")
        
        # Send in background thread
        thread = Thread(target=send_request)
        thread.daemon = True
        thread.start()