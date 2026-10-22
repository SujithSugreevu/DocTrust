"""
Middleware for system-settings enforcement.

MaintenanceModeMiddleware — returns HTTP 503 to non-admin users when maintenance mode is active.
SessionIdleTimeoutMiddleware — expires sessions after configurable idle period.
"""

import logging
import time

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("systemsettings")

# Paths that are always accessible, even during maintenance
MAINTENANCE_EXEMPT_PATHS = (
    "/api/health/",
    "/api/auth/csrf/",
    "/api/auth/login/",
    "/api/auth/logout/",
    "/api/admin/system-settings/",
    "/admin/",
)


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    When maintenance_mode is True in SystemSettings, returns HTTP 503
    to all non-admin, non-exempt requests.

    Admin users (is_admin_role) bypass the gate so they can disable
    maintenance mode through the settings API.
    """

    def process_request(self, request):
        # Never block exempt paths
        path = request.path
        for exempt in MAINTENANCE_EXEMPT_PATHS:
            if path.startswith(exempt):
                return None

        # Import lazily to avoid circular imports and allow tests to run
        # before migrations are applied.
        try:
            from systemsettings.services import get_system_settings
            settings_obj = get_system_settings()
        except Exception:
            # If the settings table doesn't exist yet, allow all requests
            return None

        if not settings_obj.maintenance_mode:
            return None

        # Allow admins through
        user = getattr(request, "user", None)
        if user and hasattr(user, "is_admin_role") and user.is_admin_role:
            return None

        return JsonResponse(
            {
                "detail": "DocTrust is currently undergoing maintenance. Please try again later.",
                "maintenance": True,
            },
            status=503,
        )


class SessionIdleTimeoutMiddleware(MiddlewareMixin):
    """
    Expire sessions when the user has been idle longer than
    ``session_idle_timeout_minutes`` from SystemSettings.

    Sets ``_last_activity`` in the session on every authenticated request.
    If the gap between now and the stored timestamp exceeds the configured
    idle timeout, the session is flushed and a 401 is returned.
    """

    def process_request(self, request):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return None

        try:
            from systemsettings.services import get_system_settings
            settings_obj = get_system_settings()
            idle_timeout_seconds = settings_obj.session_idle_timeout_minutes * 60
        except Exception:
            return None

        now = time.time()
        last_activity = request.session.get("_last_activity")

        if last_activity is not None:
            elapsed = now - last_activity
            if elapsed > idle_timeout_seconds:
                request.session.flush()
                return JsonResponse(
                    {"detail": "Session expired due to inactivity. Please log in again."},
                    status=401,
                )

        # Update last activity timestamp
        request.session["_last_activity"] = now
        return None
