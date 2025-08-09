"""
This module provides the Brevo (Sendinblue) email service implementation
using Django's built-in SMTP backend. It handles sending emails for various
notifications such as welcome emails, weekly digests, password resets, and
movie recommendations.  
"""

from django.core.mail import send_mail, send_mass_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BrevoEmailService:
    """
    Brevo (Sendinblue) email service using Django's built-in SMTP backend
    Handles all email notifications for the application
    """
    
    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.subject_prefix = getattr(settings, 'EMAIL_SUBJECT_PREFIX', '')
    
    def send_email(self, to_email: str, subject: str, template_name: str = None, 
                   context: Dict = None, html_content: str = None) -> bool:
        """Send single email using Django's send_mail"""
        try:
            full_subject = f"{self.subject_prefix}{subject}"
            
            if template_name:
                # Render from template - FIXED PATH
                html_message = render_to_string(f'emails/{template_name}.html', context or {})
                plain_message = strip_tags(html_message)
            else:
                # Use provided HTML content
                html_message = html_content
                plain_message = strip_tags(html_content) if html_content else subject
            
            result = send_mail(
                subject=full_subject,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Email sent to {to_email}: {subject}")
            
            # Log email activity for analytics
            self._log_email_activity(to_email, subject, 'email_sent')
            
            return result == 1
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            self._log_email_activity(to_email, subject, 'email_failed')
            return False
    
    def send_bulk_emails(self, email_data: List[Dict]) -> int:
        """Send multiple emails using send_mass_mail"""
        try:
            messages = []
            for email in email_data:
                full_subject = f"{self.subject_prefix}{email['subject']}"
                
                if email.get('template_name'):
                    # FIXED PATH
                    html_content = render_to_string(
                        f"emails/{email['template_name']}.html",
                        email.get('context', {})
                    )
                    plain_content = strip_tags(html_content)
                else:
                    html_content = email.get('html_content', '')
                    plain_content = strip_tags(html_content) if html_content else email['subject']
                
                # send_mass_mail doesn't support HTML, so we'll use individual sends
                # In production, consider using a proper bulk email solution
                messages.append((
                    full_subject,
                    plain_content,
                    self.from_email,
                    [email['to_email']]
                ))
            
            result = send_mass_mail(messages, fail_silently=False)
            logger.info(f"Bulk emails sent: {result}/{len(messages)}")
            
            # Log bulk email activity
            for email in email_data:
                self._log_email_activity(email['to_email'], email['subject'], 'email_sent')
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send bulk emails: {e}")
            return 0
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new user"""
        return self.send_email(
            to_email=user_email,
            subject="Welcome to Movie Recommendations!",
            template_name="welcome",
            context={
                'user_name': user_name,
                'app_name': 'Movie Recommendation System',
                'login_url': settings.SITE_URL + '/login/' if hasattr(settings, 'SITE_URL') else 'https://yourapp.com/login/',
                'support_email': settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else 'support@yourapp.com'
            }
        )
    
    def send_recommendation_digest(self, user_email: str, user_name: str, 
                                  recommendations: List[Dict]) -> bool:
        """Send weekly recommendation digest"""
        return self.send_email(
            to_email=user_email,
            subject="Your Weekly Movie Recommendations",
            template_name="weekly_digest",
            context={
                'user_name': user_name,
                'recommendations': recommendations,
                'app_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://yourapp.com',
                'unsubscribe_url': settings.SITE_URL + '/unsubscribe/' if hasattr(settings, 'SITE_URL') else 'https://yourapp.com/unsubscribe/'
            }
        )
    
    def send_password_reset_email(self, user_email: str, reset_link: str) -> bool:
        """Send password reset email"""
        return self.send_email(
            to_email=user_email,
            subject="Reset Your Password",
            template_name="password_reset",
            context={
                'reset_link': reset_link,
                'app_name': 'Movie Recommendation System'
            }
        )
    
    def send_movie_recommendation_email(self, user_email: str, user_name: str, 
                                      movie_title: str, movie_url: str) -> bool:
        """Send individual movie recommendation email"""
        return self.send_email(
            to_email=user_email,
            subject=f"New Movie Recommendation: {movie_title}",
            template_name="movie_recommendation",
            context={
                'user_name': user_name,
                'movie_title': movie_title,
                'movie_url': movie_url,
                'app_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://yourapp.com'
            }
        )
    
    def _log_email_activity(self, email: str, subject: str, action_type: str):
        """Log email activity to analytics"""
        try:
            from analytics.models import UserActivityLog
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Try to find user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = None
            
            # Only log if user exists (since your model requires authenticated users)
            if user:
                UserActivityLog.log_activity(
                    action_type='email_open' if 'sent' in action_type else 'email_click',
                    session_id=None,
                    ip_address=None,
                    user_agent='Email Service',
                    source='email',
                    User=user,
                    referer=None,
                    metadata={
                        'email_subject': subject,
                        'email_recipient': email,
                        'email_status': action_type
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log email activity: {e}")

    def send_welcome_email_async(self, user_id):
        """Send welcome email asynchronously"""
        # Import inside function to avoid circular import
        from apps.notifications.tasks import send_welcome_email_task
        return send_welcome_email_task.delay(user_id)
    
    def send_email_async(self, to_email, subject, template_name, context=None):
        """Send any email asynchronously"""
        # Import inside function to avoid circular import
        from apps.notifications.tasks import send_email_task
        return send_email_task.delay(to_email, subject, template_name, context)