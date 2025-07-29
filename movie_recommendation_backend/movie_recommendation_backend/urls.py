"""
URL configuration for movie_recommendation_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.shortcuts import render
from .views import landing_page


# Fixed schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Movie Recommendation API",
        default_version='v1',
        description="Enterprise-level movie recommendation system",
        contact=openapi.Contact(email="api@movierecommendation.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


urlpatterns = [
    path('authentication/admin/', admin.site.urls),
    path('', landing_page, name='landing_page'),
    # Authentication endpoints
    path('authentication/api/v1/auth/', include('apps.authentication.urls')),
    # Future app URLs (we'll add these as we build more apps)
    # path('api/v1/movies/', include('apps.movies.urls')),
    # path('api/v1/recommendations/', include('apps.recommendations.urls')),
    # path('api/v1/notifications/', include('apps.notifications.urls')),
    # path('api/v1/analytics/', include('apps.analytics.urls')),
    
    # API Documentation (fix the paths)
    path('authentication/api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('authentication/api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('authentication/api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
