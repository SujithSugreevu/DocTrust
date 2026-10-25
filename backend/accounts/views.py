from django.conf import settings
from django.contrib.auth import HASH_SESSION_KEY, SESSION_KEY, authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsActiveUser, IsAdminRole
from accounts.authentication import TabSessionAuthentication, create_tab_session
from auditlog.helpers import log_event, trigger_failed_login_protection
from auditlog.models import AuditEvent
from accounts.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
    ProfileUpdateSerializer,
    PasswordChangeSerializer,
    UserSuspendSerializer,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
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


def invalidate_user_sessions(user):
    session_keys = []
    sessions = Session.objects.filter(expire_date__gt=timezone.now()).only(
        "session_key",
        "session_data",
    )
    for session in sessions.iterator(chunk_size=200):
        if session.get_decoded().get(SESSION_KEY) == str(user.pk):
            session_keys.append(session.session_key)

    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()


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

        from django.db.models import Q
        attempted_user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()

        # Check suspension and auto-expiry if account exists
        if attempted_user:
            attempted_user.check_and_update_suspension()
            if attempted_user.status == User.Status.SUSPENDED:
                log_event(
                    actor=attempted_user,
                    action=AuditEvent.Action.LOGIN_FAILED,
                    target=attempted_user,
                    request=request,
                    metadata={"reason": "account_suspended"},
                )
                detail = "Your account has been suspended by an administrator."
                if attempted_user.suspension_reason:
                    detail += f" Reason: {attempted_user.suspension_reason}."
                if attempted_user.suspension_end:
                    detail += f" Suspension ends on {attempted_user.suspension_end.strftime('%d %b %Y, %H:%M UTC')}."
                return Response({"detail": detail, "suspended": True}, status=status.HTTP_403_FORBIDDEN)

        user = authenticate(request, username=identifier, password=password)

        # Uniform rejection for non-existent, bad password, inactive, or suspended accounts
        if not user or not user.is_active or user.status != User.Status.ACTIVE:
            log_event(
                actor=attempted_user,
                action=AuditEvent.Action.LOGIN_FAILED,
                target=attempted_user,
                request=request,
                metadata={"reason": "invalid_credentials"},
            )
            trigger_failed_login_protection(identifier, request, attempted_user)
            return Response(
                {"detail": "Invalid credentials or account is inactive."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Enforce role matching BEFORE creating an authenticated session
        if user.role != expected_role:
            log_event(
                actor=user,
                action=AuditEvent.Action.LOGIN_FAILED,
                target=user,
                request=request,
                metadata={"reason": "role_mismatch"},
            )
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

        tab_session_key = create_tab_session(user, remember_me)

        log_event(
            actor=user,
            action=AuditEvent.Action.LOGIN_SUCCESS,
            target=user,
            request=request,
        )

        response_data = UserSerializer(user).data
        response_data["tab_session_key"] = tab_session_key
        response = Response(response_data, status=status.HTTP_200_OK)
        response["Cache-Control"] = "no-store"
        return response


class LogoutView(APIView):
    """
    Terminates the current user session.
    """
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def post(self, request):
        enforce_csrf(request)
        log_event(
            actor=request.user,
            action=AuditEvent.Action.LOGOUT,
            target=request.user,
            request=request,
        )
        request.auth.delete()
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """
    Returns the currently authenticated user's profile and role.
    Allows updating profile name and email via PATCH.
    """
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]
    # Session verification must not share the dashboard's high-volume API
    # bucket. It remains throttled, but under its own narrow scope.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "session_verification"

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request):
        enforce_csrf(request)
        serializer = ProfileUpdateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = serializer.validated_data.get("name", "").strip()
        email = serializer.validated_data["email"].strip().lower()
        user = request.user

        if name:
            parts = name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""

        user.email = email
        user.save(update_fields=["first_name", "last_name", "email", "updated_at"])

        log_event(
            actor=user,
            action=AuditEvent.Action.USER_UPDATE,
            target=user,
            request=request,
            metadata={"updated_fields": ["name", "email"]},
        )
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class AdminOnlyCheckView(APIView):
    """
    Administrative check endpoint enforcing server-side ADMIN role authorization.
    """
    authentication_classes = [TabSessionAuthentication]
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

        log_event(
            actor=user,
            action=AuditEvent.Action.PASSWORD_RESET,
            target=user,
            request=request,
        )

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
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def get(self, request):
        two_factor = get_or_create_two_factor(request.user)
        remaining = request.user.two_factor_recovery_codes.filter(is_used=False).count()
        return Response({
            "is_enabled": two_factor.is_enabled,
            "enabled": two_factor.is_enabled,
            "enabled_at": two_factor.enabled_at if two_factor.is_enabled else None,
            "mfa_required_by_policy": is_mfa_required_for_user(request.user),
            "recovery_codes_remaining": remaining if two_factor.is_enabled else 0,
        }, status=status.HTTP_200_OK)


class TwoFactorEnrollView(APIView):
    """
    POST /api/auth/2fa/enroll/
    Initiates 2FA setup by generating a candidate TOTP secret, provisioning URI, and QR code.
    Does not activate 2FA until confirmed via verify-enroll.
    """
    authentication_classes = [TabSessionAuthentication]
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
    authentication_classes = [TabSessionAuthentication]
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
    authentication_classes = [TabSessionAuthentication]
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
        tab_session_key = create_tab_session(user, remember_me)

        log_event(
            actor=user,
            action=AuditEvent.Action.LOGIN_SUCCESS,
            target=user,
            request=request,
        )

        response_data = UserSerializer(user).data
        response_data["tab_session_key"] = tab_session_key
        if method == "recovery_code":
            remaining = user.two_factor_recovery_codes.filter(is_used=False).count()
            response_data["recovery_code_used"] = True
            response_data["recovery_codes_remaining"] = remaining

        response = Response(response_data, status=status.HTTP_200_OK)
        response["Cache-Control"] = "no-store"
        return response


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
            tab_session_key = create_tab_session(user, remember_me)

            log_event(
                actor=user,
                action=AuditEvent.Action.LOGIN_SUCCESS,
                target=user,
                request=request,
            )

            response = Response({
                "detail": "Two-factor authentication successfully configured.",
                "recovery_codes": recovery_codes,
                "user": UserSerializer(user).data,
                "tab_session_key": tab_session_key,
            }, status=status.HTTP_200_OK)
            response["Cache-Control"] = "no-store"
            return response
        except ValidationError as err:
            msg = err.message if hasattr(err, "message") else str(err)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """
    POST /api/auth/password-change/
    Authenticated password change requiring current password verification.
    Validates new password with Django password validators and updates session auth hash.
    """
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUser]

    def post(self, request):
        enforce_csrf(request)
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]

        if not request.user.check_password(current_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=request.user)
        except ValidationError as err:
            return Response(
                {"detail": "Password does not meet requirements.", "errors": list(err.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save()

        request.auth[HASH_SESSION_KEY] = request.user.get_session_auth_hash()
        request.auth.save()

        log_event(
            actor=request.user,
            action=AuditEvent.Action.PASSWORD_CHANGE,
            target=request.user,
            request=request,
        )
        return Response({"detail": "Password has been updated successfully."}, status=status.HTTP_200_OK)


class AdminUserListView(APIView):
    """
    GET  /api/admin/users/ — List all users with filtering, search and pagination
    POST /api/admin/users/ — Create a new user account
    """
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        from django.db.models import Q
        search = request.query_params.get("search", "").strip()
        role = request.query_params.get("role", "").strip()
        user_status = request.query_params.get("status", "").strip()
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("pageSize", request.query_params.get("page_size", 20)))))
        except (TypeError, ValueError):
            return Response({"detail": "Page and page size must be integers."}, status=status.HTTP_400_BAD_REQUEST)

        role_key = role.upper()
        if role_key not in ("", "ALL ROLES", "ADMIN", "ADMINISTRATOR", "EMPLOYEE"):
            return Response({"detail": "Invalid role filter."}, status=status.HTTP_400_BAD_REQUEST)

        status_key = user_status.upper()
        if status_key not in ("", "ALL STATUSES", "ACTIVE", "SUSPENDED"):
            return Response({"detail": "Invalid status filter."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = User.objects.all().order_by("-date_joined")

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        if role_key not in ("", "ALL ROLES"):
            role_value = User.Role.ADMIN if role_key in ("ADMIN", "ADMINISTRATOR") else User.Role.EMPLOYEE
            queryset = queryset.filter(role=role_value)

        # Check and update suspension expiry for users
        users_list = list(queryset)
        for u in users_list:
            u.check_and_update_suspension()

        # Re-filter if status was specified
        if status_key not in ("", "ALL STATUSES"):
            expected_status = User.Status.ACTIVE if status_key == "ACTIVE" else User.Status.SUSPENDED
            users_list = [u for u in users_list if u.status == expected_status]

        total = len(users_list)
        start = (page - 1) * page_size
        paged_users = users_list[start : start + page_size]

        return Response({
            "results": UserSerializer(paged_users, many=True).data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        enforce_csrf(request)
        serializer = AdminUserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = serializer.validated_data["name"].strip()
        email = serializer.validated_data["email"].strip().lower()
        role = serializer.validated_data["role"]
        password = serializer.validated_data.get("password")

        parts = name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        # Derive a unique username
        base_username = email.split("@")[0].replace(".", "_")
        username = base_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            status=User.Status.ACTIVE,
        )

        if password:
            user.set_password(password)
        else:
            import secrets
            user.set_password(secrets.token_urlsafe(16))
        user.save()

        log_event(
            actor=request.user,
            action=AuditEvent.Action.USER_CREATE,
            target=user,
            request=request,
            metadata={"role": role, "email": email},
        )

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(APIView):
    """
    GET   /api/admin/users/<int:pk>/ — Get user detail
    PATCH /api/admin/users/<int:pk>/ — Edit user name, email, role
    """
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_object(self, pk):
        try:
            user = User.objects.get(pk=pk)
            user.check_and_update_suspension()
            return user
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        enforce_csrf(request)
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserUpdateSerializer(data=request.data, context={"user_id": pk})
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid input.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = serializer.validated_data.get("name")
        email = serializer.validated_data.get("email")
        role = serializer.validated_data.get("role")

        updated_fields = []
        if name is not None:
            parts = name.strip().split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
            updated_fields.append("name")

        if email:
            user.email = email.strip().lower()
            updated_fields.append("email")

        if role:
            # Prevent demoting the last active administrator
            if user.role == User.Role.ADMIN and role != User.Role.ADMIN:
                admin_count = User.objects.filter(role=User.Role.ADMIN, status=User.Status.ACTIVE).exclude(pk=user.pk).count()
                if admin_count == 0:
                    return Response({"detail": "Cannot demote the only active Administrator."}, status=status.HTTP_400_BAD_REQUEST)
            user.role = role
            updated_fields.append("role")

        user.save()

        log_event(
            actor=request.user,
            action=AuditEvent.Action.USER_UPDATE,
            target=user,
            request=request,
            metadata={"updated_fields": updated_fields},
        )

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class AdminUserSuspendView(APIView):
    """
    POST /api/admin/users/<int:pk>/suspend/
    Suspends a user account with optional custom duration and reason.
    """
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @transaction.atomic
    def post(self, request, pk):
        enforce_csrf(request)
        try:
            target_user = User.objects.select_for_update().get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_user.role != User.Role.EMPLOYEE or target_user.is_admin_role:
            return Response(
                {"detail": "Only Employee accounts can be suspended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_user.pk == request.user.pk:
            return Response({"detail": "You cannot suspend your own administrator account."}, status=status.HTTP_400_BAD_REQUEST)

        target_user.check_and_update_suspension()

        if target_user.status == User.Status.SUSPENDED:
            return Response({"detail": "This account is already suspended."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserSuspendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Invalid input.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        from datetime import timedelta

        duration_days = serializer.validated_data.get("duration_days")
        duration_hours = serializer.validated_data.get("duration_hours")
        suspension_end = serializer.validated_data.get("suspension_end")
        reason = serializer.validated_data.get("reason", "Administrative suspension")

        now = timezone.now()
        computed_end = None
        if suspension_end:
            computed_end = suspension_end
        elif duration_days is not None:
            computed_end = now + timedelta(days=duration_days)
        elif duration_hours is not None:
            computed_end = now + timedelta(hours=duration_hours)

        target_user.status = User.Status.SUSPENDED
        target_user.suspended_at = now
        target_user.suspension_end = computed_end
        target_user.suspension_reason = reason
        target_user.suspended_by = request.user
        target_user.save(update_fields=["status", "suspended_at", "suspension_end", "suspension_reason", "suspended_by"])
        invalidate_user_sessions(target_user)

        log_event(
            actor=request.user,
            action=AuditEvent.Action.USER_SUSPEND,
            target=target_user,
            request=request,
            metadata={
                "suspension_reason": reason,
                "suspension_end": computed_end.isoformat() if computed_end else "indefinite",
            },
        )

        return Response({
            "detail": f"{target_user.username}'s account has been suspended.",
            "user": UserSerializer(target_user).data,
        }, status=status.HTTP_200_OK)


class AdminUserUnsuspendView(APIView):
    """
    POST /api/admin/users/<int:pk>/unsuspend/
    Lifts suspension early and reactivates account.
    """
    authentication_classes = [TabSessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @transaction.atomic
    def post(self, request, pk):
        enforce_csrf(request)
        try:
            target_user = User.objects.select_for_update().get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_user.role != User.Role.EMPLOYEE or target_user.is_admin_role:
            return Response(
                {"detail": "Only Employee accounts can be reactivated through this action."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user.check_and_update_suspension()
        if target_user.status != User.Status.SUSPENDED:
            return Response({"detail": "This account is not suspended."}, status=status.HTTP_400_BAD_REQUEST)

        target_user.status = User.Status.ACTIVE
        target_user.suspended_at = None
        target_user.suspension_end = None
        target_user.suspension_reason = ""
        target_user.suspended_by = None
        target_user.save(update_fields=["status", "suspended_at", "suspension_end", "suspension_reason", "suspended_by"])

        log_event(
            actor=request.user,
            action=AuditEvent.Action.USER_ACTIVATE,
            target=target_user,
            request=request,
            metadata={"reason": "administrative_reactivation"},
        )

        return Response({
            "detail": f"{target_user.username}'s account has been reactivated.",
            "user": UserSerializer(target_user).data,
        }, status=status.HTTP_200_OK)
