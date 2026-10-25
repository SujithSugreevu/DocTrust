"""
Serializers for AuditEvent — read-only representations for the Permission Audits UI.

Security notes:
- All serializers are read-only; no create/update operations are exposed.
- The 'metadata' field is sanitized at write time (see helpers.py), and again
  filtered here to avoid leaking any unexpected keys added via direct DB access.
"""

from rest_framework import serializers
from auditlog.models import AuditEvent
from auditlog.helpers import ALLOWED_METADATA_KEYS, FAIL_ACTIONS


class AuditEventListSerializer(serializers.ModelSerializer):
    """Compact representation for the audit log table."""

    actor_username = serializers.SerializerMethodField()
    actor_role = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()
    outcome = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "timestamp",
            "actor_username",
            "actor_role",
            "action",
            "action_display",
            "target_type",
            "target_id",
            "ip_address",
            "outcome",
        ]
        read_only_fields = fields

    def get_actor_username(self, obj):
        if obj.actor:
            return obj.actor.username
        return "System"

    def get_actor_role(self, obj):
        if obj.actor:
            return getattr(obj.actor, "role", "UNKNOWN")
        return "SYSTEM"

    def get_action_display(self, obj):
        return obj.get_action_display()

    def get_outcome(self, obj):
        """Derive outcome from metadata or action type."""
        metadata = obj.metadata or {}
        if metadata.get("status"):
            return str(metadata["status"])
        if obj.action in FAIL_ACTIONS:
            return "Failed"
        return "Success"


class AuditEventDetailSerializer(serializers.ModelSerializer):
    """Full representation for the event detail view."""

    actor_username = serializers.SerializerMethodField()
    actor_role = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()
    outcome = serializers.SerializerMethodField()
    safe_metadata = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "timestamp",
            "actor_username",
            "actor_role",
            "action",
            "action_display",
            "target_type",
            "target_id",
            "ip_address",
            "outcome",
            "safe_metadata",
        ]
        read_only_fields = fields

    def get_actor_username(self, obj):
        if obj.actor:
            return obj.actor.username
        return "System"

    def get_actor_role(self, obj):
        if obj.actor:
            return getattr(obj.actor, "role", "UNKNOWN")
        return "SYSTEM"

    def get_action_display(self, obj):
        return obj.get_action_display()

    def get_outcome(self, obj):
        metadata = obj.metadata or {}
        if metadata.get("status"):
            return str(metadata["status"])
        if obj.action in FAIL_ACTIONS:
            return "Failed"
        return "Success"

    def get_safe_metadata(self, obj):
        """Return sanitized metadata — only allowlisted keys."""
        if not obj.metadata:
            return {}
        return {
            k: v
            for k, v in obj.metadata.items()
            if k in ALLOWED_METADATA_KEYS
        }


class SecurityAlertSerializer(serializers.ModelSerializer):
    """Serializer for SecurityAlert records."""
    target_username = serializers.SerializerMethodField()
    resolved_by_username = serializers.SerializerMethodField()

    class Meta:
        from auditlog.models import SecurityAlert
        model = SecurityAlert
        fields = [
            "id",
            "title",
            "severity",
            "status",
            "scope",
            "alert_type",
            "details",
            "target_user",
            "target_username",
            "ip_address",
            "resolved_by",
            "resolved_by_username",
            "resolved_at",
            "resolution_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_target_username(self, obj):
        return obj.target_user.username if obj.target_user else "N/A"

    def get_resolved_by_username(self, obj):
        return obj.resolved_by.username if obj.resolved_by else None

