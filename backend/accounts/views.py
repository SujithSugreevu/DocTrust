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
    TwoFactorVerifyEnrollSerializer,
    TwoFactorDisableSerializer,
    TwoFactorLoginVerifySerializer,
    TwoFactorLoginSetupSerializer,
)
from accounts.two_factor_service import (
    generate_login_challenge_token,
    verify_login_challenge_token,
    start_enrollment,
    verify_enrollment,
    verify_login_factor,
    disable_two_factor,
    is_mfa_required_for_user,
    get_or_create_two_factor,
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

        # 1. Two-Factor Authentication enforcement when enabled
        if user.has_2fa_enabled:
            mfa_token = generate_login_challenge_token(user, remember_me=remember_me)
            return Response(
                {
                    "mfa_required": True,
                    "mfa_token": mfa_token,
                    "method": "totp",
                    "detail": "Two-factor authentication code required.",
                },
                status=status.HTTP_200_OK,
            )

        # 2. Mandatory Administrator MFA policy check (require_mfa_admins)
        if is_mfa_required_for_user(user):
            mfa_token = generate_login_challenge_token(user, remember_me=remember_me)
            return Response(
                {
                    "mfa_required": True,
                    "mfa_setup_required": True,
                    "mfa_token": mfa_token,
                    "detail": "Two-factor authentication is mandatory for administrators. Setup required.",
                },
                status=status.HTTP_200_OK,
            )

        # Neither 2FA nor mandatory policy applies: establish authenticated session
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


class TwoFactorStatusView(APIView):
    """
    GET /api/auth/2fa/status/
    Returns 2FA status, policy requirement, and remaining recovery codes for current user.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def get(self, request):
        two_factor = get_or_create_two_factor(request.user)
        remaining = request.user.two_factor_recovery_codes.filter(is_used=False).count()
        return Response({
            "enabled": two_factor.is_enabled,
            "enabled_at": two_factor.enabled_at,
            "mfa_required_by_policy": is_mfa_required_for_user(request.user),
            "recovery_codes_remaining": remaining,
        }, status=status.HTTP_200_OK)


class TwoFactorEnrollView(APIView):
    """
    POST /api/auth/2fa/enroll/
    Initiates 2FA setup by generating a candidate TOTP secret, provisioning URI, and QR code.
    Does not activate 2FA until confirmed via verify-enroll.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def post(self, request):
        enforce_csrf(request)
        try:
            data = start_enrollment(request.user)
            return Response(data, status=status.HTTP_200_OK)
        except ValidationError as err:
            msg = err.message if hasattr(err, "message") else str(err)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorVerifyEnrollView(APIView):
    """
    POST /api/auth/2fa/verify-enroll/
    Verifies candidate TOTP code and activates 2FA.
    Returns 8 single-use recovery codes shown only once.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def post(self, request):
        enforce_csrf(request)
        serializer = TwoFactorVerifyEnrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = serializer.validated_data["code"]
        try:
            recovery_codes = verify_enrollment(request.user, code, request=request)
            return Response({
                "detail": "Two-factor authentication enabled successfully.",
                "recovery_codes": recovery_codes,
                "user": UserSerializer(request.user).data,
            }, status=status.HTTP_200_OK)
        except ValidationError as err:
            msg = err.message if hasattr(err, "message") else str(err)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorDisableView(APIView):
    """
    POST /api/auth/2fa/disable/
    Disables 2FA. Requires verifying current password plus valid TOTP or recovery code.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def post(self, request):
        enforce_csrf(request)
        serializer = TwoFactorDisableSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = serializer.validated_data["password"]
        code = serializer.validated_data["code"]

        try:
            disable_two_factor(request.user, password, code, request=request)
            return Response({
                "detail": "Two-factor authentication has been disabled.",
                "user": UserSerializer(request.user).data,
            }, status=status.HTTP_200_OK)
        except ValidationError as err:
            msg = err.message if hasattr(err, "message") else str(err)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorLoginVerifyView(APIView):
    """
    POST /api/auth/2fa/verify-login/
    Verifies second factor (TOTP or recovery code) using login challenge token.
    On success, establishes the authenticated Django session.
    """
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        enforce_csrf(request)
        serializer = TwoFactorLoginVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mfa_token = serializer.validated_data["mfa_token"]
        code = serializer.validated_data["code"]

        try:
            user, remember_me = verify_login_challenge_token(mfa_token)
            success, method = verify_login_factor(user, code, request=request)
        except ValidationError as err:
            msg = err.message if hasattr(err, "message") else str(err)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        user.backend = "accounts.backends.EmailOrUsernameBackend"
        login(request, user)

        if remember_me:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        else:
            request.session.set_expiry(0)

        response_data = UserSerializer(user).data
        if method == "recovery_code":
            remaining = user.two_factor_recovery_codes.filter(is_used=False).count()
            response_data["recovery_code_used"] = True
            response_data["recovery_codes_remaining"] = remaining

        return Response(response_data, status=status.HTTP_200_OK)


class TwoFactorLoginSetupView(APIView):
    """
    POST /api/auth/2fa/setup-login/
    Enables safe enrollment during login when administrator MFA is mandatory by policy.
    Supports action="start" (returns QR code) and action="verify" (verifies code, activates 2FA, logs in).
    """
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        enforce_csrf(request)
        action = request.data.get("action", "verify")
        mfa_token = request.data.get("mfa_token")

        if not mfa_token:
            return Response({"detail": "Login challenge token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user, remember_me = verify_login_challenge_token(mfa_token)
        except ValidationError as err:
            msg = err.message if hasattr(err, "message") else str(err)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        if action == "start":
            try:
                enroll_data = start_enrollment(user)
                return Response(enroll_data, status=status.HTTP_200_OK)
            except ValidationError as err:
                msg = err.message if hasattr(err, "message") else str(err)
                return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        # Default action is verify
        serializer = TwoFactorLoginSetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Invalid input.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data["code"]
        try:
            recovery_codes = verify_enrollment(user, code, request=request)
            user.backend = "accounts.backends.EmailOrUsernameBackend"
            login(request, user)

            if remember_me:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)

            return Response({
                "detail": "Two-factor authentication successfully configured.",
                "recovery_codes": recovery_codes,
                "user": UserSerializer(user).data,
            }, status=status.HTTP_200_OK)
        except ValidationError as err:
            msg = err.message if hasattr(err, "message") else str(err)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
