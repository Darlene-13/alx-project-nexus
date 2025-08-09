# notifications/services/__init__.py
"""
Notification services module.
Contains all notification-related services like email, SMS, push notifications, etc.
"""

from .email_service import BrevoEmailService

# Export main services
__all__ = [
    'BrevoEmailService',
]

# Convenience imports - you can add more services here as you build them
# from .sms_service import SMSService
# from .push_service import PushNotificationService

# __all__ += ['SMSService', 'PushNotificationService']