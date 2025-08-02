from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has a `user` attribute.
    """

    def has_permission(self, request, view):
        """
        Grant permission to authenticated users for safe methods,
        and to authenticated users for unsafe methods.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Read permissions are allowed for any authenticated request,
        so we'll always allow GET, HEAD or OPTIONS requests.
        Write permissions are only allowed to the owner of the object.
        """
        # Read permissions are allowed for any authenticated request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object
        return obj.user == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit objects.
    Regular authenticated users can only read.
    """

    def has_permission(self, request, view):
        """
        Read permissions for authenticated users,
        Write permissions only for admin users.
        """
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions only for admin users
        return request.user and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        """
        Read permissions for authenticated users,
        Write permissions only for admin users.
        """
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions only for admin users
        return request.user and request.user.is_staff


class IsExperimentCreatorOrAdmin(permissions.BasePermission):
    """
    Custom permission for experiment management.
    Only the creator or admin can modify experiments.
    """

    def has_permission(self, request, view):
        """
        All authenticated users can read experiments,
        Only staff can create new experiments.
        """
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Only staff can create experiments
        return request.user and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        """
        Read permissions for any authenticated user,
        Write permissions for experiment creator or admin.
        """
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions for experiment creator or admin
        return (request.user and 
                (request.user.is_staff or obj.created_by == request.user))


class CanAccessAnalytics(permissions.BasePermission):
    """
    Permission for accessing analytics endpoints.
    Only staff members can access analytics data.
    """

    def has_permission(self, request, view):
        """
        Only staff members can access analytics.
        """
        return request.user and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        """
        Only staff members can access analytics objects.
        """
        return request.user and request.user.is_staff


class IsRecommendationOwner(permissions.BasePermission):
    """
    Permission to ensure users can only access their own recommendations.
    """

    def has_permission(self, request, view):
        """
        All authenticated users can access recommendations.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Users can only access their own recommendations.
        Staff can access all recommendations.
        """
        if request.user.is_staff:
            return True
        
        return obj.user == request.user


class CanManageExperiments(permissions.BasePermission):
    """
    Permission for managing A/B testing experiments.
    Only staff members can manage experiments.
    """

    def has_permission(self, request, view):
        """
        Read access for authenticated users,
        Write access only for staff.
        """
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        return request.user and request.user.is_staff


class IsUserProfileOwner(permissions.BasePermission):
    """
    Permission to ensure users can only access/modify their own profile data.
    Works with User model fields for recommendations.
    """

    def has_permission(self, request, view):
        """
        All authenticated users can access profile endpoints.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Users can only access/modify their own profile data.
        Staff can access all user profiles.
        """
        if request.user.is_staff:
            return True
        
        # For User model objects, check if it's the same user
        return obj == request.user