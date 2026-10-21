"""
Role-based permissions for DocTrust document and folder management.
"""

from rest_framework.permissions import BasePermission
from accounts.models import User


class IsEmployee(BasePermission):
    """
    Allows access only to authenticated users who possess the EMPLOYEE role and ACTIVE status.
    ADMIN users are explicitly denied access to private documents and folders.
    """
    message = "Employee privileges are required to access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.status == User.Status.ACTIVE
            and request.user.role == User.Role.EMPLOYEE
        )
