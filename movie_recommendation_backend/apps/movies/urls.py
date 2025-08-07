"""
This is the URL configuration for the movies app in the movie recommendation backend.
The urls are defined based on our views.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from .views import (
    MovieViewSet,
)