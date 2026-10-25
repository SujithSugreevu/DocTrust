"""
Middleware for system-settings enforcement.

SessionIdleTimeoutMiddleware — expires Django-cookie sessions after a fixed 30-minute idle period.
REST API tab sessions enforce the same timeout in TabSessionAuthentication.
"""

import logging
import time

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("systemsettings")

# Safe default: 30 minutes idle timeout (previously configurable)
SESSION_IDLE_TIMEOUT_SECONDS = 30 * 60


class SessionIdleTimeoutMiddleware(MiddlewareMixin):
    """
    Expire non-API sessions when the user has been idle longer than 30 minutes.

    REST API requests are handled by TabSessionAuthentication, which tracks
    activity on the per-tab Django session instead of the shared browser cookie.
    """

    def process_request(self, request):
        if getattr(request, "path", "").startswith("/api/"):
            return None

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return None

        now = time.time()
        last_activity = request.session.get("_last_activity")

        if last_activity is not None:
            elapsed = now - last_activity
            if elapsed > SESSION_IDLE_TIMEOUT_SECONDS:
                request.session.flush()
                return JsonResponse(
                    {"detail": "Session expired due to inactivity. Please log in again."},
                    status=401,
                )

        # Update last activity timestamp
        request.session["_last_activity"] = now
        return None
