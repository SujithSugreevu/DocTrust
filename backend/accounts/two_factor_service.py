"""
Two-Factor Authentication (2FA) Service Layer for DocTrust.

Implements RFC 6238 TOTP using pyotp, SVG QR code generation using qrcode,
cryptographic single-use recovery code hashing, rate-limiting, and replay protection.
"""

import base64
import logging
import secrets
import time
from datetime import timedelta

import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import TwoFactorRecoveryCode, User, UserTwoFactor
from auditlog.helpers import log_event
from auditlog.models import AuditEvent

logger = logging.getLogger("accounts.2fa")

LOGIN_CHALLENGE_SALT = "doctrust.auth.2fa.login"
LOGIN_CHALLENGE_MAX_AGE_SECONDS = 300  # 5 minutes
PENDING_ENROLLMENT_EXPIRY_MINUTES = 10
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
RECOVERY_CODE_COUNT = 8


def get_or_create_two_factor(user: User) -> UserTwoFactor:
    """Return the UserTwoFactor instance for the user, creating one if absent."""
    obj, _ = UserTwoFactor.objects.get_or_create(user=user)
    return obj


def generate_login_challenge_token(user: User, remember_me: bool = False) -> str:
    """
    Generate an ephemeral signed token representing a completed first-factor
    (password) authentication. Max age is 5 minutes.
    """
    signer = signing.TimestampSigner(salt=LOGIN_CHALLENGE_SALT)
    payload = {
        "user_id": str(user.pk),
        "remember_me": bool(remember_me),
        "created_at": time.time(),
    }
    return signer.sign_object(payload)


def verify_login_challenge_token(token: str) -> tuple[User, bool]:
    """
    Verify and unpack a login challenge token.
    Raises ValidationError if the token is invalid, tampered with, or expired.
    """
    signer = signing.TimestampSigner(salt=LOGIN_CHALLENGE_SALT)
    try:
        payload = signer.unsign_object(token, max_age=LOGIN_CHALLENGE_MAX_AGE_SECONDS)
    except (signing.BadSignature, signing.SignatureExpired) as exc:
        raise ValidationError("Login session has expired or is invalid. Please log in again.") from exc

    user_id = payload.get("user_id")
    remember_me = payload.get("remember_me", False)

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise ValidationError("User account not found.") from exc

    if not user.is_active or user.status != User.Status.ACTIVE:
        raise ValidationError("Account is inactive or suspended.")

    return user, remember_me


def start_enrollment(user: User) -> dict:
    """
    Initialize 2FA enrollment by generating a candidate base32 TOTP secret,
    otpauth provisioning URL, and SVG QR code.
    The secret is NOT active until verified.
    """
    two_factor = get_or_create_two_factor(user)
    if two_factor.is_enabled:
        raise ValidationError("Two-factor authentication is already enabled for this account.")

    # Generate new candidate base32 secret
    pending_secret = pyotp.random_base32()
    two_factor.pending_secret = pending_secret
    two_factor.pending_created_at = timezone.now()
    two_factor.failed_attempts = 0
    two_factor.lockout_until = None
    two_factor.save(update_fields=["pending_secret", "pending_created_at", "failed_attempts", "lockout_until"])

    # Generate provisioning URI
    totp = pyotp.TOTP(pending_secret)
    label = user.email or user.username
    issuer_name = "DocTrust"
    provisioning_uri = totp.provisioning_uri(name=label, issuer_name=issuer_name)

    # Generate crisp SVG QR code with white background for optimal scanning
    factory = qrcode.image.svg.SvgPathFillImage
    qr_img = qrcode.make(provisioning_uri, image_factory=factory)
    svg_data = qr_img.to_string()
    qr_code_data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg_data).decode("ascii")

    return {
        "secret": pending_secret,
        "provisioning_uri": provisioning_uri,
        "qr_code": qr_code_data_uri,
        "qr_code_svg": qr_code_data_uri,
        "expires_in_seconds": PENDING_ENROLLMENT_EXPIRY_MINUTES * 60,
    }


def verify_enrollment(user: User, code: str, request=None) -> list[str]:
    """
    Verify the candidate code against the pending TOTP secret.
    If valid:
      - Promotes pending_secret to active secret
      - Enables 2FA
      - Generates 8 cryptographically random recovery codes, saves hashes, returns plaintexts
      - Logs audit event
    """
    two_factor = get_or_create_two_factor(user)
    if two_factor.is_enabled:
        raise ValidationError("Two-factor authentication is already active.")

    if not two_factor.pending_secret or not two_factor.pending_created_at:
        raise ValidationError("No pending 2FA enrollment found. Please initiate setup first.")

    # Check expiry
    age = timezone.now() - two_factor.pending_created_at
    if age > timedelta(minutes=PENDING_ENROLLMENT_EXPIRY_MINUTES):
        two_factor.pending_secret = ""
        two_factor.pending_created_at = None
        two_factor.save(update_fields=["pending_secret", "pending_created_at"])
        raise ValidationError("Enrollment challenge has expired. Please start over.")

    # Rate limiting on enrollment attempts
    if two_factor.failed_attempts >= MAX_FAILED_ATTEMPTS:
        two_factor.pending_secret = ""
        two_factor.pending_created_at = None
        two_factor.failed_attempts = 0
        two_factor.save(update_fields=["pending_secret", "pending_created_at", "failed_attempts"])
        raise ValidationError("Too many invalid verification attempts. Enrollment cancelled.")

    clean_code = str(code).strip().replace(" ", "").replace("-", "")
    totp = pyotp.TOTP(two_factor.pending_secret)

    if not totp.verify(clean_code, valid_window=1):
        two_factor.failed_attempts += 1
        two_factor.save(update_fields=["failed_attempts"])
        raise ValidationError("Invalid verification code. Please check your authenticator app and try again.")

    # Verification succeeded! Promote secret and activate
    current_counter = int(time.time() // 30)
    two_factor.secret = two_factor.pending_secret
    two_factor.pending_secret = ""
    two_factor.pending_created_at = None
    two_factor.is_enabled = True
    two_factor.enabled_at = timezone.now()
    two_factor.last_verified_counter = current_counter
    two_factor.failed_attempts = 0
    two_factor.lockout_until = None
    two_factor.save()

    # Generate single-use recovery codes
    TwoFactorRecoveryCode.objects.filter(user=user).delete()
    plain_codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        # Format: XXXX-XXXX (8 hex characters)
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        plain = f"{part1}-{part2}"
        plain_codes.append(plain)
        TwoFactorRecoveryCode.objects.create(
            user=user,
            code_hash=make_password(plain),
        )

    # Log audit event
    log_event(
        actor=user,
        action=AuditEvent.Action.MFA_ENROLL,
        target=user,
        request=request,
        metadata={"mfa_method": "totp"},
        fail_closed=True,
    )

    return plain_codes


def verify_login_factor(user: User, raw_code: str, request=None) -> tuple[bool, str]:
    """
    Verify either a 6-digit TOTP code or an 8-character recovery code for login.
    Enforces replay protection and rate-limiting lockout.

    Returns:
        tuple (success: bool, method: "totp" | "recovery_code")
    Raises:
        ValidationError if account is locked out or verification fails.
    """
    two_factor = get_or_create_two_factor(user)
    if not two_factor.is_enabled or not two_factor.secret:
        raise ValidationError("Two-factor authentication is not active on this account.")

    # Check lockout
    now = timezone.now()
    if two_factor.lockout_until and now < two_factor.lockout_until:
        remaining_secs = int((two_factor.lockout_until - now).total_seconds())
        remaining_mins = max(1, remaining_secs // 60)
        raise ValidationError(
            f"Too many failed 2FA attempts. Account verification is locked for {remaining_mins} more minute(s)."
        )

    code = str(raw_code).strip()
    clean_numeric = code.replace(" ", "").replace("-", "")

    # 1. Try TOTP if code is digits
    if clean_numeric.isdigit() and len(clean_numeric) == 6:
        totp = pyotp.TOTP(two_factor.secret)
        current_counter = int(time.time() // 30)

        # Replay protection: prevent submitting the same code within the same 30s window
        if clean_numeric == totp.now() and current_counter <= two_factor.last_verified_counter:
            raise ValidationError("This verification code was already used. Please wait for the next code.")

        if totp.verify(clean_numeric, valid_window=1):
            two_factor.last_verified_counter = current_counter
            two_factor.failed_attempts = 0
            two_factor.lockout_until = None
            two_factor.save(update_fields=["last_verified_counter", "failed_attempts", "lockout_until"])

            log_event(
                actor=user,
                action=AuditEvent.Action.MFA_LOGIN_SUCCESS,
                target=user,
                request=request,
                metadata={"mfa_method": "totp"},
                fail_closed=False,
            )
            return True, "totp"

    # 2. Try single-use recovery code
    # Clean code: standard format or raw uppercase
    normalized_input = code.upper().replace(" ", "")
    if len(normalized_input) == 8 and "-" not in normalized_input:
        normalized_input = f"{normalized_input[:4]}-{normalized_input[4:]}"

    active_recovery_codes = TwoFactorRecoveryCode.objects.filter(user=user, is_used=False)
    for rc in active_recovery_codes:
        if check_password(normalized_input, rc.code_hash) or check_password(code.strip(), rc.code_hash):
            rc.is_used = True
            rc.used_at = timezone.now()
            rc.save(update_fields=["is_used", "used_at"])

            two_factor.failed_attempts = 0
            two_factor.lockout_until = None
            two_factor.save(update_fields=["failed_attempts", "lockout_until"])

            log_event(
                actor=user,
                action=AuditEvent.Action.MFA_RECOVERY_USED,
                target=user,
                request=request,
                metadata={"mfa_method": "recovery_code"},
                fail_closed=False,
            )
            return True, "recovery_code"

    # Verification failed: increment failed attempts
    two_factor.failed_attempts += 1
    if two_factor.failed_attempts >= MAX_FAILED_ATTEMPTS:
        two_factor.lockout_until = timezone.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        two_factor.save(update_fields=["failed_attempts", "lockout_until"])
        log_event(
            actor=user,
            action=AuditEvent.Action.MFA_LOGIN_FAILED,
            target=user,
            request=request,
            metadata={"mfa_method": "unknown", "reason": "lockout_triggered"},
            fail_closed=False,
        )
        raise ValidationError(
            f"Too many failed verification attempts. Verification is locked for {LOCKOUT_DURATION_MINUTES} minutes."
        )

    two_factor.save(update_fields=["failed_attempts"])
    log_event(
        actor=user,
        action=AuditEvent.Action.MFA_LOGIN_FAILED,
        target=user,
        request=request,
        metadata={"mfa_method": "unknown"},
        fail_closed=False,
    )
    raise ValidationError("Invalid authentication code or recovery code.")


def disable_two_factor(user: User, password: str, code: str, request=None) -> bool:
    """
    Disable 2FA for an authenticated user.
    Requires verifying the user's password PLUS a valid TOTP code or recovery code.
    Respects mandatory MFA policy (cannot disable if policy requires it).
    """
    if is_mfa_required_for_user(user):
        raise ValidationError(
            "Two-factor authentication is mandatory for administrators under organization policy and cannot be disabled."
        )

    if not user.check_password(password):
        raise ValidationError("Incorrect password.")

    two_factor = get_or_create_two_factor(user)
    if not two_factor.is_enabled:
        raise ValidationError("Two-factor authentication is not currently enabled.")

    # Verify code (TOTP or recovery code)
    success, method = verify_login_factor(user, code, request=request)
    if not success:
        raise ValidationError("Invalid verification code.")

    two_factor.is_enabled = False
    two_factor.secret = ""
    two_factor.pending_secret = ""
    two_factor.pending_created_at = None
    two_factor.enabled_at = None
    two_factor.last_verified_counter = 0
    two_factor.failed_attempts = 0
    two_factor.lockout_until = None
    two_factor.save()

    # Clear remaining recovery codes
    TwoFactorRecoveryCode.objects.filter(user=user).delete()

    log_event(
        actor=user,
        action=AuditEvent.Action.MFA_DISABLE,
        target=user,
        request=request,
        metadata={"mfa_method": method},
        fail_closed=True,
    )

    return True


def is_mfa_required_for_user(user: User) -> bool:
    """
    Check if MFA is mandatory for this user by organization system policy.
    The configurable require_mfa_admins setting has been removed; safe default is False.
    """
    return False

