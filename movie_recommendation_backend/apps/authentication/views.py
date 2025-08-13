"""
Authentication views for the movie recommendation backend

This file contains the API views for the user authentication system and profile management. 
It uses DRF and class based views for clean and readable code structure.
The views handle, http requests, authentication, data validation, business logic execution and logging and monitoring
"""

import json
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import update_last_login
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError
from django.db import models

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User
from .serializers import (
    LoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    UserDeviceSerializer,
    UserMinimalSerializer,
    UserStatsSerializer,
)

from ipware import get_client_ip
from apps.notifications.tasks import send_welcome_email_task

# Configuration of logging
logger = logging.getLogger(__name__)

#Logger for user activity
activity_logger = logging.getLogger('user_activity')

# WEB INTERFACE VIEWS
def auth_hub(request):
    """Authentication app hub showing all available endpoints"""
    
    # CORRECTED endpoints that match your actual URL patterns
    endpoints_by_section = {
        "🔐 AUTHENTICATION": [
            {"method": "POST", "url": "/authentication/auth/register/", "description": "🆕 User registration - Create new account", "status": "✅ Active"},
            {"method": "POST", "url": "/authentication/auth/login/", "description": "🔑 User login - Get JWT tokens", "status": "✅ Active"},
            {"method": "POST", "url": "/authentication/auth/logout/", "description": "🚪 User logout - End session", "status": "✅ Active"},
            {"method": "POST", "url": "/authentication/auth/token/refresh/", "description": "🔄 Refresh JWT token", "status": "✅ Active"},
            {"method": "POST", "url": "/authentication/auth/token/verify/", "description": "✅ Verify JWT token", "status": "✅ Active"},
        ],
        
        "👤 USER PROFILE MANAGEMENT": [
            {"method": "GET", "url": "/authentication/auth/users/", "description": "👥 List users / Get current profile", "status": "✅ Active"},
            {"method": "GET", "url": "/authentication/auth/users/{id}/", "description": "🔍 Get specific user profile", "status": "✅ Active"},
            {"method": "PUT", "url": "/authentication/auth/users/{id}/", "description": "✏️ Update user profile (full)", "status": "✅ Active"},
            {"method": "PATCH", "url": "/authentication/auth/users/{id}/", "description": "📝 Update user profile (partial)", "status": "✅ Active"},
            {"method": "DELETE", "url": "/authentication/auth/users/{id}/", "description": "🗑️ Deactivate user account", "status": "✅ Active"},
        ],
        
        "🔧 USER ACTIONS": [
            {"method": "POST", "url": "/authentication/auth/users/change-password/", "description": "🔒 Change password", "status": "✅ Active"},
            {"method": "POST", "url": "/authentication/auth/users/update-device/", "description": "📱 Update device info", "status": "✅ Active"},
            {"method": "GET", "url": "/authentication/auth/users/stats/", "description": "📊 Get user statistics", "status": "✅ Active"},
        ],
        
        "🔍 UTILITY ENDPOINTS": [
            {"method": "GET", "url": "/authentication/auth/search/", "description": "🔎 Search users", "status": "✅ Active"},
            {"method": "GET", "url": "/authentication/auth/debug/", "description": "🐛 Debug info (dev only)", "status": "🟡 Dev Only"},
        ],
        
        "📘 API DOCUMENTATION": [
            {"method": "GET", "url": "/authentication/api/docs/", "description": "📖 Swagger UI documentation", "status": "✅ Active"},
            {"method": "GET", "url": "/authentication/api/redoc/", "description": "📋 ReDoc documentation", "status": "✅ Active"},
            {"method": "GET", "url": "/authentication/api/schema/", "description": "📄 JSON API schema", "status": "✅ Active"},
        ],
        
        "🌐 WEB INTERFACE": [
            {"method": "GET", "url": "/authentication/", "description": "🏠 Authentication hub (this page)", "status": "✅ Active"},
            {"method": "GET", "url": "/authentication/admin/", "description": "⚙️ Django admin interface", "status": "✅ Active"},
        ]
    }
    
    # Flatten endpoints for template
    flat_endpoints = []
    for section_name, section_endpoints in endpoints_by_section.items():
        for endpoint in section_endpoints:
            endpoint['section'] = section_name
            flat_endpoints.append(endpoint)
    
    # Add usage examples
    usage_examples = {
        "🔑 Login Flow": [
            "1. POST /authentication/auth/register/ - Create account",
            "2. POST /authentication/auth/login/ - Get tokens", 
            "3. GET /authentication/auth/users/ - Get your profile (with token)",
            "4. PATCH /authentication/auth/users/{your_id}/ - Update profile"
        ],
        "📱 Profile Management": [
            "1. GET /authentication/auth/users/ - See your profile",
            "2. POST /authentication/auth/users/change-password/ - Change password",
            "3. POST /authentication/auth/users/update-device/ - Update device info",
            "4. GET /authentication/auth/users/stats/ - View your stats"
        ],
        "🔍 Search & Discovery": [
            "1. GET /authentication/auth/search/?q=john - Search users",
            "2. GET /authentication/auth/users/{id}/ - View other profiles",
            "3. GET /authentication/auth/debug/ - Debug info (dev)"
        ]
    }
    
    context = {
        'app_name': '🔐 Authentication API Hub',
        'app_description': 'JWT-based authentication system with comprehensive user management',
        'endpoints_by_section': endpoints_by_section,
        'flat_endpoints': flat_endpoints,
        'usage_examples': usage_examples,
        'total_endpoints': len(flat_endpoints),
        'base_url': '/authentication/auth/',
    }
    
    return render(request, 'authentication/auth_hub.html', context)

def safe_json_loads(value, default=None):
    """Safely parse JSON data that might already be parsed"""
    if value is None:
        return default or []
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return default or []
    return default or []

def log_user_action(user, action, details=None, request=None):
    """
    Utility function to log user actions consistently.
    """
    log_data = {
        'user_id': user.id if user else None,
        'username': user.username if user else None,
        'action': action,
        'details': details,
        'timestamp': timezone.now().isoformat(),
    }

    # Add request metadata if available
    if request:
        log_data['ip_address'] = get_client_ip(request)
        log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
    else:
        # Set defaults when no request is provided
        log_data['ip_address'] = 'unknown'
        log_data['user_agent'] = 'unknown'

    # Log this to the activity logger
    activity_logger.info(
        f"User Action: {log_data['action']} | User: {log_data['username']} | "
        f"IP: {log_data['ip_address']} | User Agent: {log_data['user_agent']} | "
        f"Timestamp: {log_data['timestamp']} | Details: {log_data['details']}"
    )

def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


class UserRegistrationView(APIView):
    """
    View for user registration.
    
    HTTP methods: POST
    URL: /authentication/auth/register/
    Permissions: AllowAny
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Handle User registration, returns the user profile data.
        """
        logger.info("User registration request received.")
        
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    
                    # Update last login with timestamp
                    user.last_login = timezone.now()
                    user.save()
                    
                    # Log successful registration
                    log_user_action(
                        user=user,
                        action='User Registration',
                        details={
                            'username': user.username,
                            'email': user.email,
                            'ip_address': get_client_ip(request),
                            'favorite_genres_count': len(safe_json_loads(user.favorite_genres, [])),
                            'created_at': user.date_joined.isoformat(),
                        },
                        request=request
                    )
                    
                    # 🚀 SEND WELCOME EMAIL ASYNCHRONOUSLY
                    try:
                        send_welcome_email_task.delay(user.id)
                        logger.info(f"Welcome email queued for user {user.username}")
                    except Exception as email_error:
                        # Don't fail registration if email fails
                        logger.error(f"Failed to queue welcome email for {user.username}: {email_error}")
                    
                    # Prepare response data
                    user_data = UserProfileSerializer(user).data
                    
                    logger.info(f"User {user.username} registered successfully.")
                    return Response({
                        'user': user_data,
                        'access_token': access_token,
                        'refresh_token': str(refresh),
                        'message': 'Registration successful! Welcome email sent.'
                    }, status=status.HTTP_201_CREATED)
                    
            except ValidationError as e:
                logger.error(f"Registration failed for {request.data.get('username', 'unknown')}: {str(e)}")
                return Response({
                    'error': 'Registration failed due to server error.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        else:
            logger.warning(f"Registration failed for {request.data.get('username', 'unknown')}: {serializer.errors}")
            log_user_action(
                user=None,
                action='User Registration Failed',
                details={
                    'username': request.data.get('username', 'unknown'),
                    'errors': serializer.errors,
                    'ip_address': get_client_ip(request),
                },
                request=request
            )
            return Response({
                'error': 'Invalid data provided.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """
    View for user login.
    HTTP methods: POST
    URL: /authentication/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Handle user login.
        Expects 'username' and 'password' in request data.
        Returns user profile data and JWT tokens on success.
        """
        
        logger.info("User login request received.")
        
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']

            try:
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                
                # Update last login timestamp
                user.last_login = timezone.now()
                user.save()
                
                # Log successful login
                log_user_action(
                    user=user,
                    action='User Login',
                    details={
                        'username': user.username,
                        'email': user.email,
                        'ip_address': get_client_ip(request),
                        'last_login': user.last_login.isoformat(),
                    },
                    request=request
                )
                
                # Get user profile data
                user_data = UserProfileSerializer(user).data
                logger.info(f"User {user.username} logged in successfully.")
                
                return Response({
                    'user': user_data,
                    'tokens': {
                        'access_token': access_token,
                        'refresh_token': str(refresh),
                    },
                    'message': f'Welcome back, {user.username}'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Login failed for {request.data.get('username', 'unknown')}: {str(e)}")
                return Response({
                    'error': 'Login failed due to server error.',
                    'details': str(e) if settings.DEBUG else 'Please try again'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Log failed login attempt
            identifier = request.data.get('username', 'unknown')
            logger.warning(f"Login failed for {identifier}: {serializer.errors} - {get_client_ip(request)}")
            log_user_action(
                user=None,
                action='User Login Failed',
                details={
                    'username': request.data.get('username', 'unknown'),
                    'errors': serializer.errors,
                    'ip_address': get_client_ip(request),
                },
                request=request
            )
            return Response({
                'error': 'Invalid credentials provided.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """
    View for the user logout.
    HTTP methods: POST
    URL: /authentication/auth/logout/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handle user logout.
        Only requires valid access token (in Authorization header).
        """
        try:
            logger.info(f"User {request.user.username} logged out successfully.")
            
            log_user_action(
                user=request.user,
                action='User Logout',
                details={
                    'username': request.user.username,
                    'method': 'manual',
                },
                request=request
            )
            
            return Response({
                'message': 'You have been logged out successfully.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout failed for {request.user.username}: {str(e)}")
            return Response({
                'error': 'Logout failed due to server error.',
                'details': str(e) if settings.DEBUG else 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileViewSet(ModelViewSet):
    """
    ViewSet for user profile management.
    
    HTTP methods: GET, PUT, PATCH, DELETE
    URL: /authentication/auth/users/
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Return the queryset based on user permissions.
        """
        if self.request.user.is_staff:
            return User.objects.all()
        else:
            # Regular users can only access their own profile
            return User.objects.filter(id=self.request.user.id)
    
    def get_object(self):
        """
        Get user object with permission checking.
        """
        obj = super().get_object()
        
        # Users can only access their own profile unless they're staff
        if not self.request.user.is_staff and obj.id != self.request.user.id:
            raise PermissionDenied("You can only access your own profile")
        
        return obj
    
    def get_serializer_class(self):
        """
        Returns the different serializer class based on the action.
        """
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return PasswordChangeSerializer
        elif self.action == 'update_device':
            return UserDeviceSerializer
        elif self.action == 'user_stats':
            return UserStatsSerializer
        return UserProfileSerializer

    def list(self, request):
        """
        Handle GET request to retrieve user profiles.
        For regular users, returns their own profile.
        For staff users, returns list of all users.
        """
        if request.user.is_staff:
            # Staff can see all users
            users = self.get_queryset()
            serializer = UserMinimalSerializer(users, many=True)
            
            log_user_action(
                user=request.user,
                action='User List Viewed',
                details={'user_count': len(users), 'is_staff': True},
                request=request
            )
            
            return Response({
                'users': serializer.data,
                'count': len(serializer.data),
                'message': 'User list retrieved successfully'
            }, status=status.HTTP_200_OK)
        else:
            # Regular users get their own profile
            serializer = self.get_serializer(request.user)
            
            log_user_action(
                user=request.user,
                action='User Profile Viewed',
                details={
                    'username': request.user.username,
                    'email': request.user.email,
                    'method': 'list_endpoint'
                },
                request=request
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
    
    def retrieve(self, request, pk=None):
        """
        Handle GET request to retrieve a specific user profile.
        """
        try:
            user = self.get_object()
            serializer = self.get_serializer(user)  # 🔧 FIXED: was get_serializer_class
            
            log_user_action(
                user=request.user,
                action='User Profile Viewed',
                details={
                    'viewed_user_id': user.id,
                    'viewed_username': user.username,
                    'is_self': user.id == request.user.id
                },
                request=request
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            logger.warning(f"Unauthorized access attempt to user profile {pk} by {request.user.username}.")
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Profile retrieval failed: {str(e)}")
            return Response({
                'error': 'Failed to retrieve profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, pk=None):
        """
        Handle PUT request to update the user profile.
        """
        return self._update_profile(request, partial=False)
    
    def partial_update(self, request, pk=None):
        """
        Handle PATCH request to partially update the user profile.
        """
        return self._update_profile(request, partial=True)
    
    def _update_profile(self, request, partial=False):
        """
        Helper method for profile updates.
        
        Args:
            request: HTTP request
            partial: Whether this is a partial update (PATCH vs PUT)
        """
        try:
            user = self.get_object()
            serializer = self.get_serializer(
                user, 
                data=request.data, 
                partial=partial
            )
            
            if serializer.is_valid():
                with transaction.atomic():
                    updated_user = serializer.save()
                    
                    # Log profile update
                    log_user_action(
                        user=request.user,
                        action='Profile Updated',
                        details={
                            'updated_user_id': updated_user.id,
                            'updated_fields': list(request.data.keys()),
                            'partial': partial
                        },
                        request=request
                    )
                    
                    logger.info(f"User {updated_user.username} profile updated")
                    
                    # Return updated profile data
                    response_serializer = UserProfileSerializer(updated_user)
                    return Response({
                        'user': response_serializer.data,
                        'message': 'Profile updated successfully'
                    }, status=status.HTTP_200_OK)
            
            else:
                logger.warning(f"Profile update validation failed for {request.user.username}: {serializer.errors}")
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except PermissionDenied as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Profile update failed for {request.user.username}: {str(e)}")
            return Response({
                'error': 'Profile update failed',
                'details': str(e) if settings.DEBUG else 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, pk=None):
        """
        Deactivate user account (soft delete).
        
        DELETE /authentication/auth/users/{id}/
        
        We don't actually delete the user, just deactivate the account.
        """
        try:
            user = self.get_object()
            
            with transaction.atomic():
                # Deactivate instead of deleting (for data integrity)
                user.is_active = False
                user.save()
                
                # Log account deactivation
                log_user_action(
                    user=request.user,
                    action='Account Deactivated',
                    details={
                        'deactivated_user_id': user.id,
                        'reason': 'user_request'
                    },
                    request=request
                )
                
                logger.info(f"User {user.username} deactivated their account")
                
                return Response({
                    'message': 'Account deactivated successfully. You can reactivate by contacting support.'
                }, status=status.HTTP_200_OK)
                
        except PermissionDenied as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Account deactivation failed for {request.user.username}: {str(e)}")
            return Response({
                'error': 'Account deactivation failed',
                'details': str(e) if settings.DEBUG else 'Please contact support'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # CUSTOM ACTIONS (Additional endpoints within the ViewSet)
    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """
        Change user password.
        
        POST /authentication/auth/users/change-password/
        
        Expected Input:
        {
            "current_password": "oldpassword",
            "new_password": "newpassword123",
            "new_password_confirm": "newpassword123"
        }
        """
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    # Log password change
                    log_user_action(
                        user=user,
                        action='Password Changed',
                        request=request
                    )
                    
                    logger.info(f"User {user.username} changed their password")
                    
                    return Response({
                        'message': 'Password changed successfully'
                    }, status=status.HTTP_200_OK)
                    
            except Exception as e:
                logger.error(f"Password change failed for {request.user.username}: {str(e)}")
                return Response({
                    'error': 'Password change failed',
                    'details': str(e) if settings.DEBUG else 'Please try again'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            logger.warning(f"Password change validation failed for {request.user.username}")
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='update-device')
    def update_device(self, request):
        """
        Update device information for push notifications.
        
        POST /authentication/auth/users/update-device/
        
        Expected Input:
        {
            "device_token": "firebase_token_here",
            "device_type": "ios"
        }
        """
        serializer = UserDeviceSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # Log device update
                log_user_action(
                    user=user,
                    action='Device Updated',
                    details={
                        'device_type': user.device_type,
                        'has_token': bool(user.device_token)
                    },
                    request=request
                )
                
                logger.info(f"User {user.username} updated device info")
                
                return Response({
                    'message': 'Device information updated successfully',
                    'device_type': user.device_type,
                    'has_device_token': bool(user.device_token)
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Device update failed for {request.user.username}: {str(e)}")
                return Response({
                    'error': 'Device update failed',
                    'details': str(e) if settings.DEBUG else 'Please try again'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def user_stats(self, request):
        """
        Get user statistics.
        
        GET /authentication/auth/users/stats/
        
        Returns statistics about user activity, preferences, etc.
        """
        user = request.user
        
        try:
            # Calculate user statistics from analytics if available
            try:
                from apps.analytics.models import UserActivityLog
                total_activities = UserActivityLog.objects.filter(user=user).count()
                movie_views = UserActivityLog.objects.filter(user=user, action_type='movie_view').count()
                ratings_given = UserActivityLog.objects.filter(user=user, action_type='rating_submit').count()
                favorites_added = UserActivityLog.objects.filter(user=user, action_type='favorite_add').count()
            except ImportError:
                # Fallback if analytics app is not available
                total_activities = 0
                movie_views = 0
                ratings_given = 0
                favorites_added = 0
            
            stats_data = {
                'total_interactions': total_activities,
                'movie_views': movie_views,
                'ratings_given': ratings_given,
                'favorites_added': favorites_added,
                'account_age_days': (timezone.now().date() - user.date_joined.date()).days,
                'is_active_user': user.last_login and user.last_login > timezone.now() - timedelta(days=30),
                'favorite_genres_count': len(safe_json_loads(user.favorite_genres, [])),
                'is_premium': getattr(user, 'is_premium', False),
            }
            
            serializer = UserStatsSerializer(data=stats_data)
            serializer.is_valid(raise_exception=True)
            
            # Log stats viewing
            log_user_action(
                user=user,
                action='Stats Viewed',
                request=request
            )
            
            logger.info(f"User {user.username} viewed their stats")
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Stats retrieval failed for {request.user.username}: {str(e)}")
            return Response({
                'error': 'Stats retrieval failed',
                'details': str(e) if settings.DEBUG else 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# UTILITY VIEWS
class UserSearchView(APIView):
    """
    API view to search for users (for admin purposes or social features).
    
    GET /authentication/auth/search/?q=john
    
    Note: This might be restricted based on your privacy requirements.
    """

    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Search for users by username or name.
        """
        query = request.query_params.get('q', '').strip()
        
        if len(query) < 3:
            return Response({
                'error': 'Search query must be at least 3 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Search in username, first_name, last_name
            users = User.objects.filter(
                models.Q(username__icontains=query) |
                models.Q(first_name__icontains=query) |
                models.Q(last_name__icontains=query),
                is_active=True  # Only show active users
            )[:10]  # Limit to 10 results
            
            serializer = UserMinimalSerializer(users, many=True)
            
            # Log search action
            log_user_action(
                user=request.user,
                action='User Search',
                details={'query': query, 'results_count': len(users)},
                request=request
            )
            
            logger.info(f"User {request.user.username} searched for '{query}' - {len(users)} results")
            
            return Response({
                'results': serializer.data,
                'count': len(users),
                'query': query,
                'message': f'Found {len(users)} users matching "{query}"'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"User search failed: {str(e)}")
            return Response({
                'error': 'Search failed',
                'details': str(e) if settings.DEBUG else 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# DEBUGGING AND DEVELOPMENT VIEWS

class UserDebugView(APIView):
    """
    Debug view for development (should be disabled in production).
    
    GET /authentication/auth/debug/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Return debug information about the current user.
        """
        # Only allow in DEBUG mode
        if not settings.DEBUG:
            return Response({
                'error': 'Debug endpoints are disabled in production'
            }, status=status.HTTP_404_NOT_FOUND)
        
        user = request.user
        
        try:
            debug_data = {
                'user_info': {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined,
                    'last_login': user.last_login,
                },
                'profile_info': {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone_number': getattr(user, 'phone_number', None),
                    'country': getattr(user, 'country', None),
                    'preferred_language': getattr(user, 'preferred_language', None),
                    'favorite_genres': safe_json_loads(getattr(user, 'favorite_genres', None), []),
                    'is_premium': getattr(user, 'is_premium', False),
                },
                'device_info': {
                    'device_type': getattr(user, 'device_type', None),
                    'has_device_token': bool(getattr(user, 'device_token', None)),
                },
                'request_info': {
                    'ip_address': get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'method': request.method,
                    'path': request.path,
                    'timestamp': timezone.now().isoformat(),
                },
                'system_info': {
                    'django_debug': settings.DEBUG,
                    'timezone': str(timezone.get_current_timezone()),
                    'language_code': getattr(settings, 'LANGUAGE_CODE', 'en'),
                }
            }
            
            # Add analytics info if available
            try:
                from apps.analytics.models import UserActivityLog
                recent_activities = UserActivityLog.objects.filter(
                    user=user
                ).order_by('-timestamp')[:5].values(
                    'action_type', 'timestamp', 'source'
                )
                debug_data['recent_activities'] = list(recent_activities)
            except ImportError:
                debug_data['recent_activities'] = 'Analytics app not available'
            
            # Log debug access
            log_user_action(
                user=user,
                action='Debug Info Accessed',
                details={'accessed_sections': list(debug_data.keys())},
                request=request
            )
            
            logger.info(f"Debug info accessed by {user.username}")

            return Response({
                'debug_data': debug_data,
                'message': 'Debug information retrieved successfully',
                'warning': 'This endpoint is only available in DEBUG mode'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Debug info retrieval failed for {user.username}: {str(e)}")
            return Response({
                'error': 'Failed to retrieve debug information',
                'details': str(e) if settings.DEBUG else 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# HELPER VIEW FOR PROFILE ACCESS GUIDANCE

class UserProfileHelpView(APIView):
    """
    Helper view that explains how to access user profile endpoints
    GET /authentication/auth/profile-help/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Provide help for profile access"""
        help_info = {
            "message": "User Profile Access Guide",
            "your_profile": {
                "description": "To access your own profile, use the users endpoint",
                "endpoints": {
                    "GET /authentication/auth/users/": "List users (shows your profile if authenticated)",
                    "GET /authentication/auth/users/{your_id}/": "Get your specific profile", 
                    "PATCH /authentication/auth/users/{your_id}/": "Update your profile",
                }
            },
            "authentication": {
                "description": "Include your JWT token in the Authorization header",
                "header": "Authorization: Bearer your_jwt_token_here",
                "how_to_get_token": "POST to /authentication/auth/login/ with username/password"
            },
            "current_user_info": {
                "authenticated": request.user.is_authenticated,
                "user_id": request.user.id if request.user.is_authenticated else None,
                "username": request.user.username if request.user.is_authenticated else None,
            } if request.user else {"authenticated": False},
            "quick_links": {
                "login": "/authentication/auth/login/",
                "register": "/authentication/auth/register/", 
                "your_profile": f"/authentication/auth/users/{request.user.id}/" if request.user.is_authenticated else "/authentication/auth/users/",
                "documentation": "/authentication/api/docs/"
            }
        }
        
        return Response(help_info, status=status.HTTP_200_OK)