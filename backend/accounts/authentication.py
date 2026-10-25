import time

from django.conf import settings
from django.contrib.auth import HASH_SESSION_KEY, SESSION_KEY, get_user_model
from django.contrib.auth.hashers import constant_time_compare
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.models import update_last_login
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import User


TAB_SESSION_HEADER = "HTTP_X_DOCTRUST_SESSION"
SESSION_IDLE_TIMEOUT_SECONDS = 30 * 60


class TabSessionAuthentication(SessionAuthentication):
    """Authenticate API requests only from the current tab's session key."""

    def authenticate(self, request):
        session_key = request.META.get(TAB_SESSION_HEADER)
        if not session_key:
            return None

        if len(session_key) > 64:
            raise AuthenticationFailed("Invalid session. Please log in again.")

        session = SessionStore(session_key=session_key)
        try:
            session_data = session.load()
        except (KeyError, ValueError):
            session_data = {}

        user_id = session_data.get(SESSION_KEY)
        if not user_id:
            raise AuthenticationFailed("Invalid session. Please log in again.")

        try:
            user = get_user_model().objects.get(pk=user_id)
        except (get_user_model().DoesNotExist, ValueError, TypeError):
            session.delete(session_key)
            raise AuthenticationFailed("Invalid session. Please log in again.")

        if not user.is_active:
            session.delete(session_key)
            raise AuthenticationFailed("This account is inactive.")

        user.check_and_update_suspension()
        if user.status != User.Status.ACTIVE:
            session.delete(session_key)
            raise AuthenticationFailed("This account has been suspended.")

        session_auth_hash = session_data.get(HASH_SESSION_KEY, "")
        if not session_auth_hash or not constant_time_compare(
            session_auth_hash,
            user.get_session_auth_hash(),
        ):
            session.delete(session_key)
            raise AuthenticationFailed("Invalid session. Please log in again.")

        last_activity = session_data.get("_last_activity")
        now = time.time()
        if last_activity is not None and now - last_activity > SESSION_IDLE_TIMEOUT_SECONDS:
            session.delete(session_key)
            raise AuthenticationFailed("Session expired due to inactivity. Please log in again.")

        session["_last_activity"] = now
        session.save()
        self.enforce_csrf(request)
        return user, session


def create_tab_session(user, remember_me):
    """Create an independent Django database session for one browser tab."""
    from django.contrib.auth import BACKEND_SESSION_KEY

    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = user.backend
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session["_last_activity"] = time.time()
    session.set_expiry(settings.SESSION_COOKIE_AGE if remember_me else 0)
    session.save()
    update_last_login(None, user)
    return session.session_key
