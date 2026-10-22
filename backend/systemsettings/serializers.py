"""
DRF serializer for the SystemSettings singleton.

Validates all administrator-configurable fields, enforces allowed ranges,
rejects unknown fields, and never exposes secrets or credentials.
"""

from rest_framework import serializers
from systemsettings.models import SystemSettings


# Fields that are read-only and never accepted from client input
READ_ONLY_FIELDS = {"id", "updated_at"}

# All known writable fields — anything not in this set is rejected
WRITABLE_FIELDS = {
    # Section 1
    "app_name", "support_email", "security_notifications_enabled", "maintenance_mode",
    # Section 2
    "session_idle_timeout_minutes", "max_session_lifetime_hours", "min_password_length",
    "require_mfa_admins", "require_reauth_sensitive", "failed_login_limit",
    "lockout_duration_minutes",
    # Section 3
    "allowed_file_types", "max_upload_size_mb", "user_storage_quota_mb",
    "org_storage_limit_mb", "storage_warning_threshold_pct", "block_executable_uploads",
    # Section 4
    "default_document_visibility", "allow_external_sharing", "allow_public_links",
    "default_share_permission", "allow_downloads", "allow_printing", "allow_editing",
    "require_share_expiry", "max_share_duration_days", "require_transfer_approval",
    # Section 5
    "deleted_recovery_days", "audit_retention_days", "legal_hold_enabled",
    "auto_permanent_delete", "deletion_reminder_days",
    # Section 6
    "log_document_access", "log_permission_changes", "log_failed_logins",
    "log_file_downloads", "log_admin_actions", "failed_login_alert_threshold",
    "unusual_download_alert_threshold", "alert_recipients",
    "security_notification_method",
}

VALID_FILE_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".doc", ".xls", ".ppt", ".txt", ".csv",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg",
    ".zip", ".tar", ".gz",
}

BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".com", ".msi", ".scr",
    ".ps1", ".vbs", ".js", ".jar", ".py", ".rb", ".pl",
}


class SystemSettingsSerializer(serializers.ModelSerializer):
    """
    Full serializer for SystemSettings singleton.

    Validates:
    - Unknown/unauthorized fields are rejected
    - Email fields are validated
    - Numeric fields respect min/max validators from the model
    - allowed_file_types entries are from the permitted set
    - alert_recipients entries are valid email addresses
    - app_name is not empty or excessively long
    """

    class Meta:
        model = SystemSettings
        fields = "__all__"
        read_only_fields = ["id", "updated_at"]

    def validate_app_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Application name cannot be empty.")
        if len(cleaned) > 100:
            raise serializers.ValidationError("Application name cannot exceed 100 characters.")
        return cleaned

    def validate_support_email(self, value):
        cleaned = value.strip().lower()
        if not cleaned:
            raise serializers.ValidationError("Support email cannot be empty.")
        return cleaned

    def validate_allowed_file_types(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of file extensions.")
        if len(value) > 30:
            raise serializers.ValidationError("Too many file types specified (max 30).")
        cleaned = []
        for ext in value:
            if not isinstance(ext, str):
                raise serializers.ValidationError(f"Invalid file extension entry: {ext}")
            ext = ext.strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            if ext in BLOCKED_EXTENSIONS:
                raise serializers.ValidationError(
                    f"Blocked file extension: {ext}. Executable and script files are not permitted."
                )
            if ext not in VALID_FILE_EXTENSIONS:
                raise serializers.ValidationError(
                    f"Unsupported file extension: {ext}. Allowed: {', '.join(sorted(VALID_FILE_EXTENSIONS))}"
                )
            cleaned.append(ext)
        return cleaned

    def validate_alert_recipients(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of email addresses.")
        if len(value) > 20:
            raise serializers.ValidationError("Too many alert recipients (max 20).")
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError as DjangoValidationError
        cleaned = []
        for email in value:
            if not isinstance(email, str):
                raise serializers.ValidationError(f"Invalid email entry: {email}")
            email = email.strip().lower()
            try:
                validate_email(email)
            except DjangoValidationError:
                raise serializers.ValidationError(f"Invalid email address: {email}")
            cleaned.append(email)
        return cleaned

    def validate_deletion_reminder_days(self, value):
        """Ensure deletion reminder is less than recovery period."""
        return value

    def validate(self, attrs):
        """Cross-field validation and unknown-field rejection."""
        if hasattr(self, "initial_data") and isinstance(self.initial_data, dict):
            unknown = set(self.initial_data.keys()) - WRITABLE_FIELDS - READ_ONLY_FIELDS
            if unknown:
                raise serializers.ValidationError(
                    {"detail": f"Unknown or unauthorized fields: {', '.join(sorted(unknown))}"}
                )

        # Cross-field: deletion_reminder_days must be < deleted_recovery_days
        recovery = attrs.get("deleted_recovery_days")
        reminder = attrs.get("deletion_reminder_days")
        if recovery is not None and reminder is not None and reminder >= recovery:
            raise serializers.ValidationError({
                "deletion_reminder_days": "Deletion reminder must be fewer days than the recovery period."
            })

        return attrs
