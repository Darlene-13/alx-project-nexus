"""

THis file is part of the movie recommendation backend project.
This file contains the URL configuration for the authentication app.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from apps.authentication.views import (
    UserDebugView,
    UserSearchView, 
    UserRegistrationView,
    UserProfileViewSet,
    UserLoginView,
    UserLogoutView,
) 
router = DefaultRouter()
router.register(r'users', UserProfileViewSet, basename='user-profile')
urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/',  UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('token/verify/', TokenObtainPairView.as_view(), name='token-verify'),
    path('search/', UserSearchView.as_view(), name='user-search'),
    path('debug/', UserDebugView.as_view(), name='user-debug'),

    # Include the router URLs
    path('', include(router.urls)),
]