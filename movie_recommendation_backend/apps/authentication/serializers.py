"""
This is the serializers.py file for our authentication app in the movie recommendation system
this file contains serializers for User Registration, Login, Update, Password change, Profile.
It tends to serialize the data for these operations making communication with the API easy.
"""

import json
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializes the user model for user profile related information.
    """
    # Computed fields from the model properties
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)

    # JSON field handling -Converrt JSON string to python list
    favorite_genres_list = serializers.ListField(
        child=serializers.CharField(),
        source='favorite_genres',
        allow_empty=True,
        read_only=True
    )

    # Custom field to show if user can receive push notifications
    can_receive_push = serializers.BooleanField(
        source='can_receive_push_notifications',
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'first_name', 'last_name', 'age', # Basic user information
            'date_of_birth', 'age', 'bio', 'avatar', 'country', 'preferred_timezone','preferred_language', # Profile details
            'phone_number', 'country', 'preferred_timezone',
            'favorite_genres_list',  # Preferences
            'is_active', 'is_staff', 'is_superuser', 'last_login', 'date_joined' # Status and timestamps
            'device_type', 'can_receive_push', # Device and notification preferences
        ]
        read_only_fields = ['id', 'username', 'email']

    def get_can_receive_push(self, obj):
        """
        Custom method to determine if the user can receive push notifications.
        """
        return obj.can_receive_push_notifications


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serialier for user registration (CREATE-ONLY)
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Password must be at least 8 characters long and contain a mix of letters, numbers, and special characters."
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirm your password."
    )

    # Ensure that email is required and unique
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        help_text="Enter a valid email address."
    )
    # Handle favorite genres as a list of integers
    favorite_genres = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="List of favorite genres as strings."
    )
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', # Required for registration.
                  'first_name', 'last_name', 'age', 'phone_number', 'country', 'preferred_timezone', 'favorite_genres', 'bio', 'avatar', 'device_type']
        extra_kwargs = {
            'password': {'write_only': True, 'validators': [validate_password]},
        }
    def validate_email(self, value):
        """
        Ensure that the email is unique.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def validate_username(self, value):
        """ Ensure that the username is unique."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already in use.")
    
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        return value    
    
    def validate_password(self, value):
        """
        Validate the password against Django's password validation rules.
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return value
    
    def validate_favorite_genres(self, value):
        """
        Validate that favorite genres are a list of strings.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Favorite genres must be a list.")
        for genre in value:
            if not isinstance(genre, str):
                raise serializers.ValidationError("Each genre must be a string.")
        return value
    
    def validate(self, attrs):
        """ Object level validation it validates multiple fields together."""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm', None)
        
        if password != password_confirm:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Validate the device token for type consistency
        device_type = attrs.get('device_type')
        device_token = attrs.get('device_token')
        if device_token and not device_type:
            raise serializers.ValidationError({"device_type": "Device type is required if device token is provided."})
        if device_type and not device_token:
            raise serializers.ValidationError({"device_token": "Device token is required if device type is provided."})
        return attrs
    def create(self, validated_data):
        """ Create a new user with validated data."""

        # Handle favorite genres with JSON conversion
        favorite_genres = validated_data.pop('favorite_genres', [])
        # Create user (password will be automatically hashed)
        user = User.objects.create(**validated_data)
        # Set the favorite genres as a JSON string
        if favorite_genres:
            user.set_favorite_genres(json.dumps(favorite_genres))
        user.save()
        return user

class UserUpdateSerializer(serializers.Serializer):
    """
    Serializer for user update.
    """
    #Handle favorite genres as a list
    favorite_genres = serializers.ListField(
        child = serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="List of favorite genres as strings."
    )
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Current password for the user."
    )

    class Meta:
        model = User
        fields = [
            # Profile info that can be updated
            'first_name',
            'last_name', 
            'date_of_birth',
            'bio',
            'avatar',
            'country',
            'preferred_language',
            'preferred_timezone',
            'favorite_genres',
            
            # Device info
            'device_token',
            'device_type',
            
            # Requires password confirmation
            'email',
            'current_password',
        ]
        
        extra_kwargs = {
            'current_password': {'write_only': True},
        }

    def validate_email(self, value):
        """ 
        Ensure that the email is valid and exists in the system.
        """
        user = self.instance
        value = value.lower()
        if user.email != value:
            current_password = self.initial_data.get('current_password')
            if not current_password:
                raise serializers.ValidationError("Current password is required to change email.")
            # Check if we have the correct current password
            if not user.check_password(current_password):
                raise serializers.ValidationError("Current password is incorrect.")
            
            # Check if the new email already exists
            if User.objects.filter(email=value).exclude(id=user.id).exists():
                raise serializers.ValidationError("Email is already in use.")
            # If the email is valid and unique, update the user's email
        return value
    
    def validate_favorite_genres(self, value):
        """ Validate the favorite genres list."""

        if value and len(value) > 10:
            raise serializers.ValidationError("You can only have up to 10 favorite genres.")
        return value
    

    def update(self, instance, validated_data):
        """
        Update the user instance with validated data.
        """
        # Handle favoruite genres
        favorite_genres = validated_data.pop('favorite_genres', None)

        # Remove current_password from the validated_data
        validated_data.pop('current_password', None)

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update favorite genres if provided
        if favorite_genres is not None:
            instance.set_favorite_genres(json.dumps(favorite_genres))

        instance.save()
        return instance
    

class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing the password of a user."""
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Current password for the user."
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="New password for the user."
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirm the new password."
    )

    def validate_curreny_password(self, value):
        """
        Validate the current password against the user's stored password.
        """
        user = user.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate_new_password(self, value):
        """
        Validate the new password against Django's password validation rules.
        """
        try:
            validate_password(value, user=self.context['request'].user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return value
    
    def validate(self, attrs):
        """ 
        Validate that the new password and the confirmation match.
        """
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        if new_password != new_password_confirm:
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
    
        # Ensure that the new password is different from the current password.
        current_password = attrs.get('current_password')
        if new_password == current_password:
            raise serializers.ValidationError({"new_password": "New password cannot be the same as the current password."})
        
        return attrs
    
    def save(self):
        """
        Save the newly updated password
        """
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.last_password_change = timezone.now()
        user.save()
        return user
    
class LoginSerializer(serializers.Serializer):
    """
    Serializer for the user login.
    """
    identifier = serializers.CharField(
        write_only=True,
        style={'input_type': 'text'},
        help_text="Username or email for login."
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Password for the user."
    )

    def validate(self, attrs):
        """
        Validate the user login credentials.
        """
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        # Check if the user exists by username or email
        if identifier and password:
            user = None

            if '@' in identifier:
                # If identifier is an email
                try:
                    user = User.objects.get(email=identifier)
                except User.DoesNotExist:
                    pass

            else:
                try:
                    user = User.objects.get(username=identifier)
                except User.DoesNotExist:
                    pass

        # Authenticate the user and ensure that the account is active
        if user and user.check_password(password):
            if not user.is_active:
                raise serializers.ValidationError("This account is inactive.")
            attrs['user'] = user
        else:
            raise serializers.ValidationError("Invalid credentials. Please try again.")
        return attrs
    

class UserDeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for user device information. It updates the device information for the user.
    """
    class Meta:
        model = User
        fields = ['device_token', 'device_type']
        extra_kwargs = {
            'device_token': {'required': True, 'write_only': True},
            'device_type': {'required': True, 'write_only': True},
        }

    def validate(self, value):
        """
        Validate the device token and type for consistency.
        """
        device_token = value.get('device_token')
        device_type = value.get('device_type')

        if device_token and not device_type:
            raise serializers.ValidationError({"device_type": "Device type is required if device token is provided."})
        if device_type and not device_token:
            raise serializers.ValidationError({"device_token": "Device token is required if device type is provided."})

        return value
    

# UTILITY SERIALIZERS
# These serializers are used for utilitiy purposes such as sending notifications or other non-user related tasks.
class UserMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for user information, used in notifications and other utility tasks.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = fields

class UserStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for user statistics, used in analytics and reporting.
    """
    total_interactions = serializers.IntegerField(read_only=True)
    favorite_movies_count = serializers.IntegerField(read_only=True)
    ratings_given = serializers.IntegerField(read_only=True)
    account_age_days = serializers.IntegerField(read_only=True)
    is_active_user = serializers.BooleanField(read_only=True)