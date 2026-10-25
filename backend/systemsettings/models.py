"""
Singleton system-settings model for DocTrust.

Stores all administrator-configurable settings in a single PostgreSQL row
with a CHECK constraint enforcing the singleton pattern (id=1).

Settings are grouped into logical sections mirroring the frontend:
1. General Settings (app name, support email, notifications)
2. Authentication & Security (failed login limit)
3. File Upload & Storage
4. Audit, Monitoring & Alerts
"""

from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator
from django.db import models


class SystemSettings(models.Model):
    """
    Singleton system-wide configuration row.

    Access via ``SystemSettings.load()`` which always returns the single
    instance, creating it with safe defaults on first access.
    """

    # ── Section 1: General Settings ───────────────────────────────────
    app_name = models.CharField(
        max_length=100,
        default="DocTrust",
        help_text="Application display name used in branding.",
    )
    support_email = models.EmailField(
        default="support@doctrust.local",
        help_text="Contact email shown to users and used in notifications.",
    )
    security_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Enable email notifications for security events (failed logins, permission changes).",
    )

    # ── Section 2: Authentication & Security ──────────────────────────
    failed_login_limit = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(3), MaxValueValidator(20)],
        help_text="Lock account after this many consecutive failed logins (3–20).",
    )

    # ── Section 3: File Upload & Storage ──────────────────────────────
    allowed_file_types = models.JSONField(
        default=list,
        blank=True,
        help_text='List of allowed upload file extensions, e.g. [".pdf", ".docx", ".xlsx", ".pptx"].',
    )
    max_upload_size_mb = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text="Maximum single file upload size in MB (1–500).",
    )
    user_storage_quota_mb = models.PositiveIntegerField(
        default=500,
        validators=[MinValueValidator(10), MaxValueValidator(50000)],
        help_text="Per-user storage quota in MB (10–50000).",
    )
    org_storage_limit_mb = models.PositiveIntegerField(
        default=10000,
        validators=[MinValueValidator(100), MaxValueValidator(500000)],
        help_text="Organization-wide storage limit in MB (100–500000).",
    )
    storage_warning_threshold_pct = models.PositiveIntegerField(
        default=80,
        validators=[MinValueValidator(50), MaxValueValidator(99)],
        help_text="Percentage of quota usage that triggers a warning (50–99).",
    )
    block_executable_uploads = models.BooleanField(
        default=True,
        help_text="Block uploads of executable file types (.exe, .bat, .cmd, .sh, etc.).",
    )

    # ── Section 4: Audit, Monitoring & Alerts ─────────────────────────
    log_document_access = models.BooleanField(
        default=True,
        help_text="Log document view/access events in the audit trail.",
    )
    log_permission_changes = models.BooleanField(
        default=True,
        help_text="Log permission grant/revoke events.",
    )
    log_failed_logins = models.BooleanField(
        default=True,
        help_text="Log failed login attempts.",
    )
    log_file_downloads = models.BooleanField(
        default=True,
        help_text="Log file download events.",
    )
    log_admin_actions = models.BooleanField(
        default=True,
        help_text="Log administrative actions (user management, settings changes).",
    )
    failed_login_alert_threshold = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(3), MaxValueValidator(50)],
        help_text="Number of failed logins before triggering an alert (3–50).",
    )
    alert_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="List of email addresses that receive security alerts.",
    )
    security_notification_method = models.CharField(
        max_length=20,
        choices=[("email", "Email"), ("in_app", "In-App"), ("both", "Both")],
        default="email",
        help_text="How security notifications are delivered.",
    )

    # ── Timestamps ────────────────────────────────────────────────────
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
        constraints = [
            models.CheckConstraint(
                check=models.Q(id=1),
                name="singleton_system_settings",
            ),
        ]

    def save(self, *args, **kwargs):
        """Enforce singleton: always save as id=1."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton settings row."""
        raise PermissionError("System settings cannot be deleted.")

    @classmethod
    def load(cls):
        """
        Return the singleton instance, creating it with safe defaults
        on first access (including default allowed_file_types and alert_recipients).
        """
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "allowed_file_types": [".pdf", ".docx", ".xlsx", ".pptx"],
                "alert_recipients": [],
            },
        )
        if created and not obj.allowed_file_types:
            obj.allowed_file_types = [".pdf", ".docx", ".xlsx", ".pptx"]
            obj.save(update_fields=["allowed_file_types"])
        return obj

    def __str__(self):
        return f"SystemSettings (updated {self.updated_at})"
