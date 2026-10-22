from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for DocTrust.
    Supports role-based authorization (ADMIN / EMPLOYEE) and account status.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        EMPLOYEE = "EMPLOYEE", "Employee"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        help_text="Role determining access level within DocTrust.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Account status (Active/Suspended).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser or self.is_staff

    @property
    def is_employee_role(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def has_2fa_enabled(self):
        try:
            return bool(self.two_factor.is_enabled)
        except Exception:
            return False

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class UserTwoFactor(models.Model):
    """
    Two-Factor Authentication configuration for a user.
    Stores the TOTP secret, pending enrollment state, and replay-prevention counter.
    TOTP secrets are never exposed in public serializers or API responses.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="two_factor",
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Whether 2FA is active and enforced for this user.",
    )
    secret = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Active base32-encoded TOTP secret key.",
    )
    pending_secret = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Unverified candidate secret during active enrollment.",
    )
    pending_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when pending enrollment was initiated (expires in 10 minutes).",
    )
    enabled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when 2FA was verified and activated.",
    )
    last_verified_counter = models.BigIntegerField(
        default=0,
        help_text="TOTP time-step counter of last successful verification to prevent replay attacks.",
    )
    failed_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Consecutive failed verification attempts for rate limiting.",
    )
    lockout_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Lockout timestamp if failed attempt threshold is exceeded.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status_text = "Enabled" if self.is_enabled else "Disabled"
        return f"2FA for {self.user.username} ({status_text})"


class TwoFactorRecoveryCode(models.Model):
    """
    Single-use backup recovery codes for 2FA account recovery.
    Stored securely as cryptographic password hashes (Django PBKDF2).
    Plaintext codes are shown only once upon successful enrollment.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="two_factor_recovery_codes",
    )
    code_hash = models.CharField(
        max_length=128,
        help_text="Cryptographic hash of the single-use recovery code.",
    )
    is_used = models.BooleanField(
        default=False,
        help_text="Whether this recovery code has already been consumed.",
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this recovery code was redeemed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        state = "Used" if self.is_used else "Active"
        return f"Recovery Code ({state}) for {self.user.username}"

