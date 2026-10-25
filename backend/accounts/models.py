from django.contrib.auth.models import AbstractUser
from django.db import models, transaction


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
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the user account was suspended.",
    )
    suspension_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the user account suspension expires.",
    )
    suspension_reason = models.TextField(
        blank=True,
        default="",
        help_text="Administrative justification for the account suspension.",
    )
    suspended_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="suspended_users",
        help_text="Administrator who initiated the suspension.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def check_and_update_suspension(self):
        """
        Check if account is currently suspended and whether the suspension has expired.
        If suspension_end is reached or passed, automatically unsuspend and record audit event.
        Returns True if the user remains suspended, False if active.
        """
        if self.status == self.Status.SUSPENDED:
            if self.suspension_end:
                from django.utils import timezone
                if timezone.now() >= self.suspension_end:
                    with transaction.atomic():
                        self.status = self.Status.ACTIVE
                        self.suspended_at = None
                        self.suspension_end = None
                        self.suspension_reason = ""
                        self.suspended_by = None
                        self.save(update_fields=["status", "suspended_at", "suspension_end", "suspension_reason", "suspended_by"])
                        from auditlog.helpers import log_event
                        from auditlog.models import AuditEvent
                        log_event(
                            actor=None,
                            action=AuditEvent.Action.USER_ACTIVATE,
                            target=self,
                            metadata={"reason": "automatic_suspension_expiry"},
                        )
                    return False
            return True
        return False

    @property
    def is_currently_suspended(self):
        return self.check_and_update_suspension()

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
