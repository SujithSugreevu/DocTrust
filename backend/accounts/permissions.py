from rest_framework.permissions import BasePermission
from accounts.models import User


class IsActiveUser(BasePermission):
    """
    Allows access only to authenticated users with ACTIVE status and is_active flag.
    """
    message = "Your account is not active or has been suspended."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_currently_suspended:
            return False
        return request.user.status == User.Status.ACTIVE


class IsAdminRole(BasePermission):
    """
    Allows access only to authenticated users who possess the ADMIN role or superuser rights.
    """
    message = "Administrator privileges are required to access this resource."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_currently_suspended:
            return False
        return (
            request.user.status == User.Status.ACTIVE
            and request.user.is_admin_role
        )
