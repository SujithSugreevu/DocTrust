"""
Append-only audit trail for DocTrust security-relevant actions.

IMMUTABILITY GUARANTEES & SCOPE:
- Application-Level Enforcement (ACTIVE & ENFORCED):
  * AuditEvent.save() rejects any updates on existing persisted records (raises PermissionError).
  * AuditEvent.delete() rejects deletion calls on audit records (raises PermissionError).
  * Django Admin forbids add, change, and delete operations entirely.
  * No public or private REST API endpoints expose UPDATE or DELETE for AuditEvent.
  * Point-of-recording metadata allowlist sanitization ensures sensitive data is never captured.

- Database-Level Protection (CURRENT LIMITATION):
  * The PostgreSQL table "auditlog_auditevent" does NOT currently enforce database-level
    immutability triggers (e.g. BEFORE UPDATE OR DELETE ON auditlog_auditevent RAISE EXCEPTION)
    or database-role level privilege revocations (REVOKE UPDATE, DELETE ON auditlog_auditevent).
  * Direct SQL access by a PostgreSQL superuser / DB admin, or Django ORM bulk methods
    (e.g., QuerySet.update(), which bypass model save() hooks) are not blocked at the database
    layer in this phase.
  * Database-level trigger enforcement and dedicated restricted DB roles are documented as
    planned hardening improvements for future deployment phases.
"""

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """
    Immutable audit log entry recording a security-relevant action.

    Current Phase Role Mapping:
      - EMPLOYEE = Document Owner (actions on own documents are logged)
      - ADMIN = Audit log reader only (no document content/metadata access)
      - VIEWER role is not yet implemented and is reserved as a future extension.
    """

    class Action(models.TextChoices):
        # Document lifecycle
        DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD", "Document Uploaded"
        DOCUMENT_DOWNLOAD = "DOCUMENT_DOWNLOAD", "Document Downloaded"
        DOCUMENT_DELETE = "DOCUMENT_DELETE", "Document Soft-Deleted"
        DOCUMENT_PURGE = "DOCUMENT_PURGE", "Document Purged"
        DOCUMENT_RESTORE = "DOCUMENT_RESTORE", "Document Restored"
        DOCUMENT_ARCHIVE = "DOCUMENT_ARCHIVE", "Document Archived"
        DOCUMENT_VIEW = "DOCUMENT_VIEW", "Document Metadata Viewed"
        DOCUMENT_UPDATE = "DOCUMENT_UPDATE", "Document Metadata Updated"
        DOCUMENT_SHARE = "DOCUMENT_SHARE", "Document Shared"
        DOCUMENT_SHARE_UPDATE = "DOCUMENT_SHARE_UPDATE", "Document Share Updated"
        DOCUMENT_SHARE_REVOKE = "DOCUMENT_SHARE_REVOKE", "Document Share Revoked"
        # Folder lifecycle
        FOLDER_CREATE = "FOLDER_CREATE", "Folder Created"
        FOLDER_RENAME = "FOLDER_RENAME", "Folder Renamed"
        FOLDER_DELETE = "FOLDER_DELETE", "Folder Deleted"
        # System settings & Administrative actions
        SYSTEM_SETTINGS_UPDATE = "SYSTEM_SETTINGS_UPDATE", "System Settings Updated"
        SYSTEM_SETTINGS_RESET = "SYSTEM_SETTINGS_RESET", "System Settings Reset"
        MAINTENANCE_MODE_TOGGLE = "MAINTENANCE_MODE_TOGGLE", "Maintenance Mode Toggled"
        SECURITY_ALERT = "SECURITY_ALERT", "Security Alert Triggered"
        SECURITY_ALERT_RESOLVED = "SECURITY_ALERT_RESOLVED", "Security Alert Resolved"
        # Two-Factor Authentication actions
        MFA_ENROLL = "MFA_ENROLL", "Two-Factor Authentication Enrolled"
        MFA_DISABLE = "MFA_DISABLE", "Two-Factor Authentication Disabled"
        MFA_LOGIN_SUCCESS = "MFA_LOGIN_SUCCESS", "Two-Factor Authentication Succeeded"
        MFA_LOGIN_FAILED = "MFA_LOGIN_FAILED", "Two-Factor Authentication Failed"
        MFA_RECOVERY_USED = "MFA_RECOVERY_USED", "Two-Factor Recovery Code Used"
        # Authentication lifecycle
        LOGIN_SUCCESS = "LOGIN_SUCCESS", "Login Successful"
        LOGIN_FAILED = "LOGIN_FAILED", "Login Failed"
        LOGOUT = "LOGOUT", "User Logged Out"
        # User management
        USER_CREATE = "USER_CREATE", "User Account Created"
        USER_UPDATE = "USER_UPDATE", "User Account Updated"
        USER_SUSPEND = "USER_SUSPEND", "User Account Suspended"
        USER_ACTIVATE = "USER_ACTIVATE", "User Account Activated"
        PASSWORD_CHANGE = "PASSWORD_CHANGE", "Password Changed"
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        help_text="User who performed the action. SET_NULL preserves the log if the user is deleted.",
    )
    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        db_index=True,
        help_text="The type of action that was performed.",
    )
    target_type = models.CharField(
        max_length=100,
        help_text="Dotted model label of the target object, e.g. 'documents.Document'.",
    )
    target_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary key/identifier of the target object (supports UUID strings, BigInts, or slugs).",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address at the time of the action.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Non-sensitive operational context: file_size, content_type, sha256_hash, file_extension. Never store sensitive filenames or content.",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Server timestamp when the event was recorded.",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["actor", "-timestamp"], name="audit_actor_ts_idx"),
            models.Index(fields=["action", "-timestamp"], name="audit_action_ts_idx"),
            models.Index(fields=["target_type", "target_id"], name="audit_target_idx"),
        ]
        verbose_name = "Audit Event"
        verbose_name_plural = "Audit Events"

    # ── Immutability guards ──────────────────────────────────────────

    def save(self, *args, **kwargs):
        """Allow initial creation only. Reject updates on existing records."""
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise PermissionError(
                "AuditEvent records are immutable and cannot be modified after creation."
            )
        # Defense-in-depth: enforce allowlist sanitization on initial creation
        if not self.pk:
            from auditlog.helpers import sanitize_metadata
            self.metadata = sanitize_metadata(self.metadata)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of audit records at the application level."""
        raise PermissionError(
            "AuditEvent records are immutable and cannot be deleted."
        )

    def __str__(self):
        actor_name = self.actor.username if self.actor else "system"
        return f"[{self.timestamp}] {actor_name}: {self.get_action_display()} ({self.target_type} #{self.target_id})"


class SecurityAlert(models.Model):
    """
    Security alert model for tracking security events, attacks, and alerts.
    Supports resolution status, persistence, and audit tracking.
    """

    class Severity(models.TextChoices):
        ATTACK = "Security Attack", "Security Attack"
        HIGH = "High", "High"
        MEDIUM = "Medium", "Medium"
        LOW = "Low", "Low"

    class Status(models.TextChoices):
        OPEN = "Open", "Open"
        REVIEW = "Review", "Review"
        RESOLVED = "Resolved", "Resolved"

    class Scope(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        EMPLOYEE = "EMPLOYEE", "Employee"

    title = models.CharField(max_length=200)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.HIGH,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.EMPLOYEE,
    )
    alert_type = models.CharField(max_length=100)
    details = models.TextField()
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_alerts",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_alerts",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="sec_alert_status_idx"),
            models.Index(fields=["scope", "-created_at"], name="sec_alert_scope_idx"),
        ]
        verbose_name = "Security Alert"
        verbose_name_plural = "Security Alerts"

    def __str__(self):
        return f"[{self.severity}] {self.title} ({self.status})"

