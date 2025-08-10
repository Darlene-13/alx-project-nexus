import json
import time
import uuid
import logging
from django.utils.deprecation import MiddlewareMixin
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from .models import UserActivityLog

logger = logging.getLogger(__name__)
UserActivityLoggingMiddleware = 'apps.analytics.middleware.UserActivityLoggingMiddleware'

class UserActivityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all incoming requests as user activities.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define paths to skip logging
        self.skip_paths = [
            "/static/", 
            "/media/", 
            "/admin/", 
            "/favicon.ico",
            "/health/",
            "/robots.txt"
        ]
        # Define methods to skip
        self.skip_methods = ["OPTIONS", "HEAD"]
    
    def process_request(self, request):
        """Initialize request tracking"""
        # Store start time to measure execution duration
        request.start_time = time.time()
        
        # Generate session ID for anonymous users
        if not request.session.session_key:
            request.session.create()
        request.session_id = request.session.session_key
        
        return None
    
    def process_response(self, request, response):
        """Log the completed request"""
        try:
            # Skip if path or method should be ignored
            if self._should_skip_logging(request):
                return response
            
            # Calculate execution time
            execution_time_ms = int((time.time() - getattr(request, 'start_time', time.time())) * 1000)
            
            # Determine user (or None)
            user = request.user if request.user.is_authenticated else None
            
            # Capture client info
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]  # Limit length
            referer = request.META.get("HTTP_REFERER", "")[:500]  # Limit length
            source = "web"
            
            # Determine action type based on request
            action_type = self._determine_action_type(request, response)
            
            # Prepare metadata
            metadata = {
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "execution_time_ms": execution_time_ms,
                "query_params": dict(request.GET) if request.GET else {},
                "content_length": response.get('Content-Length', 0)
            }
            
            # Add POST data size if present (don't log actual data for privacy)
            if request.method == "POST":
                metadata["has_post_data"] = bool(request.POST)
                metadata["post_data_keys"] = list(request.POST.keys()) if request.POST else []
            
            # Log the activity asynchronously to avoid blocking the response
            self._log_activity_async(
                action_type=action_type,
                session_id=request.session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                source=source,
                User=user,  # Match your model's parameter name
                referer=referer,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"[UserActivityLoggingMiddleware] Error logging activity: {e}")
            # Don't let logging errors break the response
        
        return response
    
    def _should_skip_logging(self, request):
        """Determine if this request should be logged"""
        # Skip certain paths
        if any(request.path.startswith(path) for path in self.skip_paths):
            return True
        
        # Skip certain methods
        if request.method in self.skip_methods:
            return True
        
        # Skip bot requests (optional)
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        if any(bot in user_agent for bot in ["bot", "crawler", "spider", "scraper"]):
            return True
        
        return False
    
    def _determine_action_type(self, request, response):
        """Determine the type of action based on request path and method"""
        path = request.path.lower()
        method = request.method
        
        # Map to your existing ACTION_TYPES
        # API endpoints - map to movie_view or movie_search
        if path.startswith("/api/"):
            if "movies" in path:
                return "movie_view"
            elif "search" in path:
                return "movie_search"
            elif "recommendations" in path:
                return "recommendation_click"
            else:
                return "movie_view"  # Default for API calls
        
        # Authentication actions - map to existing types
        elif "login" in path or "auth" in path:
            return "movie_view"  # Use existing type
        elif "logout" in path:
            return "movie_view"  # Use existing type
        elif "register" in path or "signup" in path:
            return "movie_view"  # Use existing type
        
        # Movie-related actions
        elif "/movies/" in path:
            if method == "POST":
                return "movie_view"  # Could be rating, favorite, etc.
            else:
                return "movie_view"
        
        # Search actions
        elif "search" in path:
            return "movie_search"
        
        # Recommendation actions
        elif "/recommend" in path:
            return "recommendation_click"
        
        # Profile/user actions
        elif "/profile" in path:
            return "movie_view"  # Use existing type
        
        # Default to movie_view for all other actions
        else:
            return "movie_view"
    
    def _log_activity_async(self, **kwargs):
        """Log activity to database with error handling"""
        try:
            # Handle anonymous users - only log if user is authenticated
            # since your model's user field appears to be required
            user = kwargs.get('User')
            if not user or not user.is_authenticated:
                # Skip logging for anonymous users since your model requires a user
                return
            
            # Use atomic transaction for data integrity
            with transaction.atomic():
                UserActivityLog.log_activity(**kwargs)
                
        except Exception as e:
            logger.error(f"Failed to log user activity: {e}")
            # Could implement fallback logging here (e.g., to file or external service)
    
    def get_client_ip(self, request):
        """Extract client IP address from request headers."""
        # Check for IP in various headers (in order of preference)
        ip_headers = [
            "HTTP_X_FORWARDED_FOR",
            "HTTP_X_REAL_IP", 
            "HTTP_X_FORWARDED",
            "HTTP_X_CLUSTER_CLIENT_IP",
            "HTTP_FORWARDED_FOR",
            "HTTP_FORWARDED",
            "REMOTE_ADDR"
        ]
        
        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one
                if "," in ip:
                    ip = ip.split(",")[0].strip()
                
                # Basic validation that it looks like an IP
                if self._is_valid_ip(ip):
                    return ip
        
        return "unknown"
    
    def _is_valid_ip(self, ip):
        """Basic IP validation"""
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            return True
        except (ValueError, AttributeError):
            return False