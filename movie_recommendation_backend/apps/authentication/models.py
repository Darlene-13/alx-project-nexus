from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
import re #Regular expressions for validation
import json
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# To ensure that the phone number is in a valid format
def validate_phone_number(value):
    if not value and re.match(r'^\+?1?\d{9,15}$', value):
        raise ValidationError(
            f'{value} is not a valid phone number. It should be in the format +999999999 or 999999999.'
        )
    
def validate_json_array(value):
    """ Custom validator to ensure that the value is a JSON array.
    This is commonly used for storing lists in a text field eg: Favorite genres field."""
    try:
        data = json.loads(value)
        if not isinstance(data, list):
            raise ValidationError(f'{value} is not a valid JSON array.')
    except (json.JSONDecodeError, TypeError):
        raise ValidationError(f'{value} is not a valid JSON array.')

class User(AbstractUser):
    """ 
    Custom user model that extends the default django user model.

    This model includes additional fields like phone number etc.
    """

    # User profile information fields
    email = models.EmailField(unique=True, help_text="Email address must be added here.")
    date_of_birth = models.DateField(null=True, blank = True, help_text="Date of birth must be added here.")
    is_premium = models.BooleanField(default=False, help_text="Indicates if the user has a premium account.")
    phone_number = models.CharField(max_length=20, validators=[validate_phone_number], help_text="Phone number must be in the format +999999999 or 999999999.")
    username = models.CharField(max_length=150, unique=True, help_text="Username must be unique.")
    first_name = models.CharField(max_length=30, blank=True, help_text="First name of the user.")
    last_name = models.CharField(max_length=30, blank=True, help_text="Last name of the user.")
    preferred_timezone = models.CharField(max_length=50, default='GMT+3')
    bio = models.TextField(blank=True, help_text="A short bio about the user.")
    avatar = models.ImageField(upload_to='user_avatars/', # File will be uploaded to media/user_avatars/
                                blank=True, null=True, help_text="User's avatar image.")
    #Preference fields
    favorite_genres = models.TextField(blank=True, 
                                       validators=[validate_json_array], help_text="A JSON array of user's favorite genres. Example: ['Action', 'Comedy', 'Drama']. This field is optional and can be left blank.")
    preferred_language = models.CharField(max_length=50, blank=True, 
                                          default='en',
                                          choices=[
                                              ('en', 'English'),
                                              ('es', 'Spanish'),
                                              ('fr', 'French'),
                                              ('de', 'German'),
                                              ('zh', 'Chinese'),
                                              ('ja', 'Japanese'),
                                              ('ru', 'Russian'),
                                              ('it', 'Italian'),
                                              ('pt', 'Portuguese'),
                                              ('hi', 'Hindi'),
                                              ('ar', 'Arabic'),
                                              ('ko', 'Korean'),   
                                          ],
                                          help_text="Preferred language of the user.")
    country = models.CharField(max_length=100, blank=True, help_text="Country of the user. This field is optional and can be left blank.")
    
    #Device information fields
    device_token = models.CharField(max_length=255, blank=True, 
                                    unique=True,
                                    null=True,
                                    help_text="Device token for push notifications. This field is optional and can be left blank.")
    device_type = models.CharField(max_length=50, blank=True, 
                                   choices=[
                                       ('android', 'Android'),
                                       ('ios', 'iOS'),
                                       ('web', 'Web'),
                                   ],
                                   null=True,
                                   help_text="Type of device used by the user. This field is optional and can be left blank.")
    
    # Account status fields
    is_active = models.BooleanField(default=True, help_text="Indicates if the user account is active.")
    is_superuser = models.BooleanField(default=False, help_text="Indicates if the user has superuser privileges.")
    is_staff = models.BooleanField(default=False, help_text="Indicates if the user can access the admin site.")
    
    # Timestamps fields
    date_joined = models.DateTimeField(auto_now_add=True, help_text="The date and time when the user joined.")  
    last_login = models.DateTimeField(default=timezone.now, help_text="The last time the user logged in.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="The date and time when the user was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="The date and time when the user was last updated.")

    class Meta:

        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

        ordering = ['-created_at']

        # Database indexes.
        indexes = [
            models.Index(fields=['email'], name='idex_users_email'),
            models.Index(fields=['username'], name='idex_users_username'),
            models.Index(fields=['is_active'], name='idx_users_is_active'),
            models.Index(fields=['device_token'], name='idx_users_device_token'),
            models.Index(fields=['country'], name='idx_users_country'),
            models.Index(fields=['created_at'], name='idx_users_created_at'),
        ]

# Custom properties and methods
@property
def full_name(self):
    """ Returns the full name of the user. if no names are provided it returns the username."""
    if self.first_name and self.last_name:
        return f"{self.first_name} {self.last_name}".strip()
    elif self.first_name:
        return self.first_name.strip()
    elif self.last_name:
        return self.last_name.strip()
    return self.username  # Fallback logic to username if no names are provided

@property
def display_name(self):
    """Returns the best available name for display purposes."""
    return self.full_name or self.username or self.email

@property
def age(self):
    """
    Calculates the age of the user based on the date of birth.
    """
    if self.date_of_birth:
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year

        # Adjust the age if the birthday has not yet occured.
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age
    
@property
def favorite_genres_list(self):
    """ Returns the favorite genres as a list."""
    try:
        return json.loads(self.favorite_genres)
    except (json.JSONDecodeError, TypeError):
        return []

def set_favorite_genres(self, genre_ids):
    """ Sets the favorite genres as a JSON array."""
    if isinstance(genre_ids, list):
        self.favorite_genres = json.dumps(genre_ids)
    else:
        raise ValueError("Genre_ids must be a list.")


def add_favorite_genre(self, genre_id):
    """ Adds a single genre to the favorite genres."""
    current_favorites = self.favorite_genres_list
    if genre_id not in current_favorites:
        current_favorites.append(genre_id)
        self.set_favorite_genres(current_favorites)

def remove_favorite_genre(self, genre_id):
    """ Removes a single genre from the favorite genres list"""
    current_favorites = self.favorite_genres_list
    if genre_id in current_favorites:
        current_favorites.remove(genre_id)
        self.set_favorite_genres(current_favorites)

def has_device_for_push(self):
    """ Checks if the user has a device token for push notifications."""
    return bool(self.device_token)

def is_adult(self):
    """ Check is the user is over 18 years of age"""
    if self.age is None:
        return None
    return self.age >= 18


def clean(self):
    """ Custom clean method to validate the user model fields"""
    super().clean()

    # Validate device token and type consistency
    if self.device_token and not self.device_type:
        raise ValidationError("Device type must be set if device token is provided.")
    if self.device_type and self.device_token is None:
        raise ValidationError("Device token must be set if device type is provided.")
    # Validate the date of birth
    if self.date_of_birth:
        today = timezone.now().date()
        if self.date_of_birth > today:
            raise ValidationError("Date of birth cannot be in the future.")
        
    # Vlidate all items are integrers (genre IDS)
    try:
        genre_ids = json.loads(self.favorite_genres)
        if not all(isinstance(genre_id, int) for genre_id in genre_ids):
            raise ValidationError("All genre IDs must be integers.")
    except (json.JSONDecodeError, TypeError):
        raise ValidationError("Favorite genres must be a valid JSON array of integers.")
    
    # Validate phone number format
    if self.phone_number:
        validate_phone_number(self.phone_number)
    # Validate timezone format
    if self.timezone:
        if not re.match(r'^[A-Za-z]+[+-][0-9]{1,2}$', self.timezone):
            raise ValidationError("Timezone must be in the format 'GMT+/-X' where X is a number between 1 and 12.")
    # Validate preferred language
    if self.preferred_language:
        valid_languages = [choice[0] for choice in self._meta.get_field('preferred_language').choices]
        if self.preferred_language not in valid_languages:
            raise ValidationError(f"Preferred language must be one of the following: {', '.join(valid_languages)}.")
        
def save(self, *args, **kwargs):
    """ Custom save method to ensure the user model is valid before saving.
    Override the save method to perfrom custom actions before saving
    """
    if self.email:
        self.email = self.email.lower().strip()
    
    # Call clean method for validation
    self.full_clean()

    # Call the parent save method
    super().save(*args, **kwargs)

def __str__(self):
    """ Returns the string representation of the user."""
    return self.display_name or self.username or self.email
    # This ensures that the string representation is always meaningful.

def __repr__(self):
    return f"<CustomUser: {self.display_name} (ID: {self.id})>"


# Signal handlers
@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Signal handler that runs after a User is saved.
    Can be used for creating related objects or logging.
    """
    if created:
        # User was just created - perform initial setup
        # Use username instead of display_name to avoid attribute issues
        print(f"New user created: {instance.username} (ID: {instance.id})")
        
        # Example: Create notification preferences automatically
        # (We'll implement this when we create the notifications app)
        pass


@receiver(pre_delete, sender=User)
def user_pre_delete(sender, instance, **kwargs):
    """
    Signal handler that runs before a User is deleted.
    Can be used for cleanup or logging.
    """
    print(f"User being deleted: {instance.username}")
    
    # Example: Clean up user's uploaded files
    if instance.avatar:
        # Delete avatar file from storage
        instance.avatar.delete(save=False)