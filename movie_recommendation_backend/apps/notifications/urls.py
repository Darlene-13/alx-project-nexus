from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationsPreferencesViewSet,
    NotificationLogViewSet,
    InAppNotificationsViewSet,
    NotificationHealthView,
    notifications_hub,  # 👈 Add this
)

app_name = 'notifications'

router = DefaultRouter()
router.register(r'preferences', NotificationsPreferencesViewSet, basename='preferences')
router.register(r'logs', NotificationLogViewSet, basename='logs')
router.register(r'inapp', InAppNotificationsViewSet, basename='inapp')
router.register(r'health', NotificationHealthView, basename='health')

urlpatterns = [
    path('', notifications_hub, name='notifications-hub'), 
    path('', include(router.urls)),
]
