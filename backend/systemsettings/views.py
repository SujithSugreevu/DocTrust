"""
REST API views for system settings (admin-only).

GET  /api/admin/system-settings/          — Read current settings + health status
PATCH /api/admin/system-settings/         — Partial update with audit trail
POST /api/admin/system-settings/reset/    — Reset to safe defaults with audit trail
"""

import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from auditlog.helpers import log_event
from auditlog.models import AuditEvent
from systemsettings.models import SystemSettings
from systemsettings.serializers import SystemSettingsSerializer
from systemsettings.services import get_system_settings, get_system_health, invalidate_settings_cache

logger = logging.getLogger("systemsettings")

# Fields that may require special processing for audit diff
SENSITIVE_DISPLAY_FIELDS = set()  # None currently — reserve for future secrets


def _safe_repr(value):
    """Convert a value to a safe string for audit metadata."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _build_change_metadata(old_settings, new_settings, changed_field_names):
    """Build audit metadata for a settings change."""
    metadata = {
        "changed_fields": ", ".join(sorted(changed_field_names)),
    }
    # Only include first changed field's old/new for brevity (the rest are in changed_fields)
    if len(changed_field_names) == 1:
        field = list(changed_field_names)[0]
        if field not in SENSITIVE_DISPLAY_FIELDS:
            old_val = getattr(old_settings, field, None)
            new_val = getattr(new_settings, field, None)
            metadata["setting_name"] = field
            metadata["old_value"] = _safe_repr(old_val)
            metadata["new_value"] = _safe_repr(new_val)
    return metadata


# Capability status indicators — accurately reflect what is and is not implemented
CAPABILITY_STATUS = {
    "mfa": {
        "available": True,
        "provider": "Authenticator App TOTP (RFC 6238)",
    },
    "malware_scanning": {
        "available": True,
        "provider": "Built-in (magic bytes, PDF script scanner, Office ZIP/macro inspector)",
        "external_scanner": False,
    },
    "unusual_download_detection": {
        "available": False,
        "reason": "Download anomaly detection logic is not yet implemented.",
    },
    "backup_monitoring": {
        "available": False,
        "reason": "No backup monitoring service is currently configured.",
    },
    "printing_enforcement": {
        "available": False,
        "reason": "Server-side print restriction cannot be enforced; this is an advisory setting only.",
    },
}


class SystemSettingsDetailView(APIView):
    """
    GET  — Return all current system settings and health status.
    PATCH — Partial update of system settings with validation and audit logging.
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        settings_obj = get_system_settings()
        serializer = SystemSettingsSerializer(settings_obj)
        data = serializer.data
        data["system_health"] = get_system_health()
        data["capabilities"] = CAPABILITY_STATUS
        return Response(data)

    def patch(self, request):
        settings_obj = get_system_settings()

        serializer = SystemSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Detect which fields actually changed
        changed_fields = set()
        for field_name, new_value in serializer.validated_data.items():
            old_value = getattr(settings_obj, field_name)
            if old_value != new_value:
                changed_fields.add(field_name)

        if not changed_fields:
            return Response(
                {"detail": "No changes detected."},
                status=status.HTTP_200_OK,
            )

        # Snapshot old state for audit
        old_snapshot = SystemSettingsSerializer(settings_obj).data

        # Check for maintenance mode toggle — requires special audit action
        maintenance_toggled = "maintenance_mode" in changed_fields
        new_maintenance = serializer.validated_data.get("maintenance_mode")

        try:
            with transaction.atomic():
                updated = serializer.save()

                # Audit: general settings change
                audit_metadata = _build_change_metadata(
                    type("OldSettings", (), old_snapshot),
                    updated,
                    changed_fields,
                )
                log_event(
                    actor=request.user,
                    action=AuditEvent.Action.SYSTEM_SETTINGS_UPDATE,
                    target=updated,
                    request=request,
                    metadata=audit_metadata,
                    fail_closed=True,
                )

                # Additional audit for maintenance mode toggle
                if maintenance_toggled:
                    log_event(
                        actor=request.user,
                        action=AuditEvent.Action.MAINTENANCE_MODE_TOGGLE,
                        target=updated,
                        request=request,
                        metadata={
                            "maintenance_mode": str(new_maintenance).lower(),
                            "setting_name": "maintenance_mode",
                        },
                        fail_closed=True,
                    )
        except Exception as exc:
            logger.error("Failed to update system settings: %s", exc)
            return Response(
                {"detail": "Failed to save settings. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        invalidate_settings_cache()

        result = SystemSettingsSerializer(updated).data
        result["system_health"] = get_system_health()
        result["capabilities"] = CAPABILITY_STATUS
        return Response(result)


class SystemSettingsResetView(APIView):
    """
    POST /api/admin/system-settings/reset/ — Reset all settings to safe defaults.
    """
    permission_classes = [IsAdminRole]

    def post(self, request):
        settings_obj = get_system_settings()

        try:
            with transaction.atomic():
                # Delete and recreate with defaults
                SystemSettings.objects.filter(pk=1).delete()
                new_settings = SystemSettings.load()

                log_event(
                    actor=request.user,
                    action=AuditEvent.Action.SYSTEM_SETTINGS_RESET,
                    target=new_settings,
                    request=request,
                    metadata={"reason": "Administrator-initiated reset to defaults"},
                    fail_closed=True,
                )
        except Exception as exc:
            logger.error("Failed to reset system settings: %s", exc)
            return Response(
                {"detail": "Failed to reset settings. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        invalidate_settings_cache()

        result = SystemSettingsSerializer(new_settings).data
        result["system_health"] = get_system_health()
        result["capabilities"] = CAPABILITY_STATUS
        return Response(result)
