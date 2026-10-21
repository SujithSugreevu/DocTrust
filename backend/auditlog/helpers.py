"""
Audit logging helper for creating immutable AuditEvent records.

Usage from views:
    from auditlog.helpers import log_event
    from auditlog.models import AuditEvent

    # Non-critical / best-effort logging (fail-open):
    # Uses ONLY explicitly allowlisted operational fields.
    # NEVER pass original_filename, raw filenames, or sensitive document content.
    log_event(
        actor=request.user,
        action=AuditEvent.Action.DOCUMENT_VIEW,
        target=document_instance,
        request=request,
        metadata={
            "file_size": 102400,
            "content_type": "application/pdf",
            "file_extension": ".pdf",
            "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
    )

    # Security-critical logging (fail-closed, transactional):
    with transaction.atomic():
        document.delete()
        log_event(
            actor=request.user,
            action=AuditEvent.Action.DOCUMENT_DELETE,
            target=document,
            request=request,
            fail_closed=True,  # Aborts and rolls back transaction on failure
        )
"""

import logging
from django.db import transaction

from auditlog.models import AuditEvent

logger = logging.getLogger("auditlog")


# ── Point-of-Recording Metadata Allowlist ─────────────────────────────
# Strict allowlist of permitted operational metadata fields.
# Raw filenames, file contents, secrets, passwords, tokens, and sensitive
# document details CANNOT be recorded in the audit trail.
ALLOWED_METADATA_KEYS = frozenset({
    "file_size",        # Operational file size in bytes (int)
    "content_type",     # Verified MIME type (str, e.g. "application/pdf")
    "sha256_hash",      # Cryptographic SHA-256 integrity hash (str)
    "sha256",           # SHA-256 alias (str)
    "file_extension",   # Normalized file extension only (str, e.g. ".pdf", ".png")
    "document_count",   # Operational document count (int)
    "page_count",       # Operational page count (int)
    "status",           # Operational status code/string (str)
    "reason",           # Controlled operational reason code (str)
})


def sanitize_metadata(raw_metadata):
    """
    Sanitize audit metadata at the point of recording using a strict allowlist.

    Guarantees:
    - Only explicitly permitted operational keys in ALLOWED_METADATA_KEYS are persisted.
    - Raw filenames, file contents, secrets, tokens, or arbitrary nested payloads
      are stripped before reaching the database.
    - Values must be primitive types (str, int, float, bool) or None.
    - Non-dict inputs safely default to an empty dictionary.
    """
    if not isinstance(raw_metadata, dict):
        return {}

    sanitized = {}
    for key, value in raw_metadata.items():
        if key in ALLOWED_METADATA_KEYS:
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
    return sanitized


class AuditLogFailureError(Exception):
    """
    Raised when an audit event write fails and fail_closed is True.
    Used for security-critical actions that must abort and roll back
    the calling transaction if the audit event cannot be persisted.
    """
    pass


def get_client_ip(request):
    """
    Extract the client IP address from the request.
    Prefers X-Forwarded-For (first entry) when behind a reverse proxy,
    falls back to REMOTE_ADDR.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_event(
    *,
    actor,
    action,
    target=None,
    request=None,
    metadata=None,
    fail_closed=False,
):
    """
    Create an immutable AuditEvent record.

    Args:
        actor:        The User who performed the action (or None for system events).
        action:       An AuditEvent.Action choice value.
        target:       The Django model instance that was acted upon (optional).
                      Supports Integer, BigInteger, and UUID primary keys.
        request:      The Django/DRF request object for IP extraction (optional).
        metadata:     A dict of operational context (optional).
                      Point-of-recording sanitization strictly filters this
                      against ALLOWED_METADATA_KEYS. Raw filenames, file contents,
                      and secrets are stripped before persistence.
        fail_closed:  If True, raises AuditLogFailureError on failure to ensure
                      the caller's transaction is aborted and rolled back.
                      If False (default), logs the error and returns None to
                      prevent non-critical logging from disrupting the caller.

    Returns:
        The created AuditEvent instance, or None if creation failed and fail_closed=False.

    Raises:
        AuditLogFailureError: If creation fails and fail_closed=True.
    """
    target_type = ""
    target_id = None

    if target is not None:
        target_type = f"{target._meta.app_label}.{target._meta.model_name}"
        if getattr(target, "pk", None) is not None:
            target_id = str(target.pk)

    ip_address = None
    if request is not None:
        ip_address = get_client_ip(request)

    # Point-of-recording allowlist sanitization
    safe_metadata = sanitize_metadata(metadata)

    try:
        # Nested transaction.atomic() creates a savepoint in PostgreSQL,
        # preventing a DB error here from corrupting the outer transaction
        # when running in fail-open mode.
        with transaction.atomic():
            event = AuditEvent.objects.create(
                actor=actor,
                action=action,
                target_type=target_type,
                target_id=target_id,
                ip_address=ip_address,
                metadata=safe_metadata,
            )
        logger.info(
            "AuditEvent recorded: actor=%s action=%s target=%s#%s",
            actor.username if actor else "system",
            action,
            target_type,
            target_id,
        )
        return event
    except Exception as exc:
        logger.exception(
            "Failed to record AuditEvent: actor=%s action=%s target=%s#%s (fail_closed=%s)",
            actor.username if actor else "system",
            action,
            target_type,
            target_id,
            fail_closed,
        )
        if fail_closed:
            raise AuditLogFailureError(
                f"Security audit logging failed for action '{action}'. "
                "Operation aborted under fail-closed security policy."
            ) from exc
        return None
