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

# WEB INTERFACE VIEWS (Add this section at the very top after imports)
def auth_hub(request):
    """Authentication app hub showing all available endpoints"""
    
    # Define your actual authentication endpoints with correct URLs
    auth_endpoints = [
        {
            'url': '/authentication/auth/register/',
            'description': 'User registration endpoint - Create new user accounts',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/login/',
            'description': 'User login endpoint - Authenticate users and get tokens',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/logout/',
            'description': 'User logout endpoint - Invalidate user sessions',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/token/refresh/',
            'description': 'JWT token refresh - Get new access token using refresh token',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/token/verify/',
            'description': 'JWT token verification - Verify and obtain token pair',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/search/',
            'description': 'User search endpoint - Search for users in the system',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/debug/',
            'description': 'Debug endpoint - Development and testing utilities',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/users/',
            'description': 'User profile management - CRUD operations for user profiles',
            'status': 'active'
        },
        {
            'url': '/authentication/auth/admin/',
            'description': 'Django admin interface - Administrative user management',
            'status': 'active'
        },
        {
            'url': '/authentication/api/docs/',
            'description': 'API documentation - Swagger UI for exploring API endpoints',
            'status': 'active'
        },
        {
            'url': '/authentication/api/redoc/',
            'description': 'API documentation - ReDoc UI for exploring API endpoints',
            'status': 'active'
        },
        {
            'url': '/authentication/api/schema/',
            'description': 'API schema - JSON schema for the authentication API',
            'status': 'active'
        },
    ]
    
    context = {
        'endpoints': auth_endpoints,
        'app_name': 'Authentication API',
        'app_description': 'RESTful JWT-based authentication system with user management'
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
    URL: /api/v1/auth/register/
    Permissions: AllowAny
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Handle User registration, returns the user profile data.
        """
        logger.info("User registration request received.")  # Fixed typo
        
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    
                    # Update last login with timestamp
                    user.last_login = timezone.now()
                    user.save()  # Don't forget to save!
                    
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
                        }
                    )
                    
                    # 🚀 SEND WELCOME EMAIL ASYNCHRONOUSLY
                    try:
                        send_welcome_email_task.delay(user.id)
                        logger.info(f"Welcome email queued for user {user.username}")
                    except Exception as email_error:
                        # Don't fail registration if email fails
                        logger.error(f"Failed to queue welcome email for {user.username}: {email_error}")
                    
                    # Prepare response data  # Fixed typo
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
                    'error': 'Registration failed due to server error.'  # Fixed typo (removed extra dot)
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
    HTTP methods:POST
    URL: /api/v1/auth/login/
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
                last_login = timezone.now()
                
                #Log sucessful login
                log_user_action(
                    user=user,
                    action='User Login',
                    details={
                        'username': user.username,
                        'email': user.email,
                        'ip_address': get_client_ip(request),
                        'last_login': last_login.isoformat(),
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
                    }, 'message': 'Welcome back, {}'.format(user.username)
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Login failed for {request.data.get('username', 'unknown')}: {str(e)}")
                return Response({
                    'error': 'Login failed due to server error.',
                    'details': str(e) if settings.DEBUG else 'Please try again'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:

            # Log failed login attempt
            identifier = request.data.get('identifier', 'unknown')
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
            return Response(
                {
                    'error': 'Invalid credentials provided.',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST
            )
class UserLogoutView(APIView):
    """
    View for the user logout.
    HTTP methods: POST
    URL: /api/v1/auth/logout/
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
    Viewset for user profile management.

    HTTP methods: GET, PUT, PATCH, DELETE
    URL: /api/v1/auth/profile/
    """
    def get_queryset(self):
        """
        Return the queryset of the user profile.
        """
        return User.objects.filter(id=self.request.user.id)
    
    def get_object(self):
        """ 
        Returns the user profile object for the current user.
        """
        return self.request.user
    
    def get_serializer_class(self):
        """
        Returns the different serializer classe based on the action."""

        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return PasswordChangeSerializer
        elif self.action == 'get_stats':
            return UserDeviceSerializer
        return UserProfileSerializer

    def list(self, request):
        """
        Handle GET request to retrieve the user profile.
        """
        serializer = self.get_serializer(request.user)
        log_user_action(
            user=request.user,
            action='User Profile Viewed',
            details={
                'username': request.user.username,
                'email': request.user.email,
                'ip_address': get_client_ip(request),
                'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
            },
            request=request
        )
        logger.info(f"User {request.user.username} profile viewed.")
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def retrieve(self, request, pk=None):
        """
        Handle GET request to retrieve the user profile.
        """

        if pk and str(pk) != str(request.user.id):
            logger.warning(f"Unauthorized access attempt to user profile {pk} by {request.user.username}.")
            return Response(
                {'error': 'You do not have permission to access this profile.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer_class(request.user)
        log_user_action(
            user=request.user,
            action='User Profile Viewed',
            details={
                'username': request.user.username,
                'email': request.user.email,
                'ip_address': get_client_ip(request),
                'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
            },
            request=request
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
    
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
        serializer = self.get_serializer(
            request.user, 
            data=request.data, 
            partial=partial
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    # Log profile update
                    log_user_action(
                        user=user,
                        action='PROFILE_UPDATED',
                        details={
                            'updated_fields': list(request.data.keys()),
                            'partial': partial
                        },
                        request=request
                    )
                    
                    logger.info(f"User {user.username} updated their profile")
                    
                    # Return updated profile data
                    response_serializer = UserProfileSerializer(user)
                    return Response({
                        'user': response_serializer.data,
                        'message': 'Profile updated successfully'
                    }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Profile update failed for {request.user.username}: {str(e)}")
                return Response({
                    'error': 'Profile update failed',
                    'details': str(e) if settings.DEBUG else 'Please try again'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            logger.warning(f"Profile update validation failed for {request.user.username}: {serializer.errors}")
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """
        Deactivate user account (soft delete).
        
        DELETE /api/v1/auth/users/{id}/
        
        We don't actually delete the user, just deactivate the account.
        """
        user = request.user
        
        try:
            with transaction.atomic():
                # Deactivate instead of deleting (for data integrity)
                user.is_active = False
                user.save()
                
                # Log account deactivation
                log_user_action(
                    user=user,
                    action='ACCOUNT_DEACTIVATED',
                    details={'reason': 'user_request'},
                    request=request
                )
                
                logger.info(f"User {user.username} deactivated their account")
                
                return Response({
                    'message': 'Account deactivated successfully. You can reactivate by contacting support.'
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Account deactivation failed for {user.username}: {str(e)}")
            return Response({
                'error': 'Account deactivation failed',
                'details': str(e) if settings.DEBUG else 'Please contact support'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


    # CUSTOM ACTIONS (Additional endpoints within the ViewSet)

    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """
        Change user password.
        
        POST /api/v1/auth/users/change-password/
        
        Expected Input:
        {
            "current_password": "oldpassword",
            "new_password": "newpassword123",
            "new_password_confirm": "newpassword123"
        }
        """
        serializer = self.get_serializer(
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
                        action='PASSWORD_CHANGED',
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
        
        POST /api/v1/auth/users/update-device/
        
        Expected Input:
        {
            "device_token": "firebase_token_here",
            "device_type": "ios"
        }
        """
        serializer = self.get_serializer(
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
                    action='DEVICE_UPDATED',
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
        
        GET /api/v1/auth/users/stats/
        
        Returns statistics about user activity, preferences, etc.
        """
        user = request.user
        
        try:
            # Calculate user statistics
            # (These would come from the user_movie_interactions table when we build it)
            stats_data = {
                'total_interactions': 0,  # Will be calculated from interactions
                'favorite_movies_count': 0,  # Will be calculated from favorites
                'ratings_given': 0,  # Will be calculated from ratings
                'account_age_days': (timezone.now().date() - user.date_joined.date()).days,
                'is_active_user': user.last_login and user.last_login > timezone.now() - timedelta(days=30),
            }
            
            serializer = UserStatsSerializer(data=stats_data)
            serializer.is_valid(raise_exception=True)
            
            # Log stats viewing
            log_user_action(
                user=user,
                action='STATS_VIEWED',
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
    
    GET /api/v1/auth/search/?q=john
    
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
                action='USER_SEARCH',
                details={'query': query, 'results_count': len(users)},
                request=request
            )
            
            return Response({
                'results': serializer.data,
                'count': len(users)
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
    
    GET /api/v1/auth/debug/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Return debug information about the current user.
        """
        # Only allow in DEBUG mode
        from django.conf import settings
        if not settings.DEBUG:
            return Response({
                'error': 'Debug endpoints are disabled in production'
            }, status=status.HTTP_404_NOT_FOUND)
        
        user = request.user
        
        debug_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
            'favorite_genres': user.favorite_genres_list,
            'device_info': {
                'device_type': user.device_type,
                'has_token': bool(user.device_token),
                'can_receive_push': user.has_device_for_push()
            },
            'request_info': {
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'method': request.method,
            }
        }
        
        logger.info(f"Debug info accessed by {user.username}")

        return Response(debug_data, status=status.HTTP_200_OK)