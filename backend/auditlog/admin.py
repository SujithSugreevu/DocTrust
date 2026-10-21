import json
from django.contrib import admin
from django.utils.html import format_html
from auditlog.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """
    Read-only admin interface for AuditEvent records.

    Security & Privacy Controls:
    - Accessible only to authorized staff users with ADMIN role.
    - No add, change, or delete permissions — audit logs are immutable.
    - List, search, and filter fields do NOT expose sensitive document filenames or contents.
    - Detail view sanitizes metadata to redact any sensitive document titles/filenames.
    """

    # Do not expose filenames or document content in list
    list_display = (
        "timestamp",
        "actor",
        "action",
        "target_type",
        "target_id",
        "ip_address",
    )
    list_filter = ("action", "target_type", "timestamp")
    # Search is restricted to identifiers and usernames; no document content search
    search_fields = ("actor__username", "target_type", "target_id", "ip_address")
    readonly_fields = (
        "actor",
        "action",
        "target_type",
        "target_id",
        "ip_address",
        "safe_metadata",
        "timestamp",
    )
    exclude = ("metadata",)
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"

    # ── Strict Role & Permission Enforcement ─────────────────────────

    def has_module_permission(self, request):
        """Allow access only to authenticated, active staff users with ADMIN role."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
            and (getattr(user, "role", None) == "ADMIN" or getattr(user, "is_superuser", False))
        )

    def has_view_permission(self, request, obj=None):
        """Allow viewing only to authenticated, active staff users with ADMIN role."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
            and (getattr(user, "role", None) == "ADMIN" or getattr(user, "is_superuser", False))
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ── Privacy Safeguards for Metadata Display ──────────────────────

    @admin.display(description="Operational Metadata (Sanitized)")
    def safe_metadata(self, obj):
        """
        Sanitize metadata to ensure no sensitive document filenames, titles,
        or contents are leaked in the Django admin UI.
        """
        if not obj.metadata:
            return format_html("<em>No metadata recorded</em>")

        SENSITIVE_KEYS = {
            "filename",
            "original_filename",
            "file_name",
            "title",
            "content",
            "body",
            "document_content",
            "text",
        }

        sanitized = {}
        for key, value in obj.metadata.items():
            if key.lower() in SENSITIVE_KEYS:
                sanitized[key] = "[REDACTED_FOR_SECURITY]"
            else:
                sanitized[key] = value

        formatted_json = json.dumps(sanitized, indent=2, sort_keys=True)
        return format_html(
            '<pre style="margin: 0; padding: 8px; background: #f8fafc; '
            'border: 1px solid #e2e8f0; border-radius: 4px; '
            'font-family: monospace; font-size: 12px;">{}</pre>',
            formatted_json,
        )
