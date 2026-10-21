from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import CSRFCheck, SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsActiveUser, IsAdminRole
from accounts.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
)


def enforce_csrf(request):
    """
    Explicitly enforce Django's CSRF check on API requests.
    """
    check = CSRFCheck(request)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f"CSRF Failed: {reason}")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFView(APIView):
    """
    Sets the CSRF cookie on the client and returns the token in the response payload.
    """
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        csrf_token = get_token(request)
        return Response({"csrfToken": csrf_token, "detail": "CSRF cookie set."})


class LoginView(APIView):
    """
    Authenticates a user via username/email and password with mandatory expected_role validation.
    Rejects invalid credentials, inactive accounts, suspended accounts, and role mismatches safely.
    """
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        enforce_csrf(request)

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        identifier = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        expected_role = serializer.validated_data["expected_role"]
        remember_me = serializer.validated_data.get("remember_me", False)

        user = authenticate(request, username=identifier, password=password)

        # Uniform rejection for non-existent, bad password, inactive, or suspended accounts
        if not user or not user.is_active or user.status != User.Status.ACTIVE:
            return Response(
                {"detail": "Invalid credentials or account is inactive."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Enforce role matching BEFORE creating an authenticated session
        if user.role != expected_role:
            return Response(
                {"detail": "Invalid credentials for the selected role. Please check your account type and try again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Session established only after credentials and expected role match
        login(request, user)

        if remember_me:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        else:
            request.session.set_expiry(0)  # Expires on browser close

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    Terminates the current user session.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf(request)
        logout(request)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """
    Returns the currently authenticated user's profile and role.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class AdminOnlyCheckView(APIView):
    """
    Administrative check endpoint enforcing server-side ADMIN role authorization.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {
                "status": "authorized",
                "message": "Welcome Administrator. Administrative access granted.",
                "user": UserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    Sends a time-limited password-reset email with a secure token.
    Uniform response prevents user enumeration.
    """
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        enforce_csrf(request)

        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid email address.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        # Only generate and send reset email for active, eligible accounts
        if user and user.is_active and user.status == User.Status.ACTIVE:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
            reset_url = f"{frontend_base}/reset-password?uid={uid}&token={token}"

            subject = "DocTrust Password Reset Request"
            message = (
                f"Hello {user.get_full_name() or user.username},\n\n"
                f"We received a request to reset your DocTrust account password.\n\n"
                f"To set a new password, click the secure link below:\n"
                f"{reset_url}\n\n"
                f"This link is valid for 1 hour. If you did not request a password reset, "
                f"no action is needed and your account remains secure.\n\n"
                f"DocTrust Security Team"
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        # Consistent confirmation response to prevent account enumeration
        return Response(
            {"detail": "If an account exists for that email, password reset instructions will be sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Validates password-reset token and saves the new password with Django password hashing.
    """
    permission_classes = [AllowAny]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        enforce_csrf(request)

        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid request.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uid_b64 = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if (
            not user
            or not user.is_active
            or user.status != User.Status.ACTIVE
            or not default_token_generator.check_token(user, token)
        ):
            return Response(
                {"detail": "The password reset link is invalid or has expired. Please request a new link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=user)
        except ValidationError as err:
            return Response(
                {"detail": "Password does not meet requirements.", "errors": list(err.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password (hashes securely with PBKDF2)
        user.set_password(new_password)
        user.save()

        # Invalidate any open sessions by updating session auth hash
        # (Django invalidates sessions whose auth hash does not match user.get_session_auth_hash())
        return Response(
            {"detail": "Password has been reset successfully. You can now log in with your new password."},
            status=status.HTTP_200_OK,
        )
