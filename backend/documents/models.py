"""
Document and Folder models for DocTrust.

Enforces:
- UUID primary keys (prevents sequential ID enumeration attacks).
- Direct ownership linked to User model with on_delete=models.PROTECT.
- Immutable storage keys and strict file integrity metadata (SHA-256, size).
- Strict database constraints for status, size, file types, and hash formats.
- Partial case-insensitive unique index on (owner, Lower(name)) for active and archived documents.
- Soft-delete, restore, retention, and purge tracking.
"""

import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import functions


class Folder(models.Model):
    """
    Folder for organizing documents belonging to a single owner.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="folders",
        help_text="User who owns this folder. Protected against deletion while folders exist.",
    )
    name = models.CharField(
        max_length=40,
        help_text="Folder name (1-40 characters).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Server timestamp when the folder was created.",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                functions.Lower("name"),
                "owner",
                name="unique_folder_owner_name_case_insensitive",
            ),
            models.UniqueConstraint(
                fields=["id", "owner"],
                name="unique_folder_id_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "created_at"], name="folder_owner_created_idx"),
        ]

    def __str__(self):
        return f"{self.name} (Owner: {self.owner_id})"


class Document(models.Model):
    """
    Document model storing private document metadata and secure storage references.
    Physical bytes are stored exclusively in private storage via storage_key.
    """

    class FileType(models.TextChoices):
        PDF = "PDF", "PDF"
        DOCX = "DOCX", "DOCX"
        XLSX = "XLSX", "XLSX"
        PPTX = "PPTX", "PPTX"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
        help_text="Owner of the document. Protected against deletion while documents exist.",
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Optional folder containing this document. Protected against deletion while documents exist.",
    )
    name = models.CharField(
        max_length=100,
        help_text="Document name including extension (1-100 characters).",
    )
    original_filename = models.CharField(
        max_length=100,
        help_text="Sanitized basename at upload time for audit purposes only.",
    )
    description = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text="Optional description (up to 300 characters).",
    )
    file_type = models.CharField(
        max_length=10,
        choices=FileType.choices,
        help_text="Validated file type (PDF, DOCX, XLSX, PPTX).",
    )
    size = models.PositiveBigIntegerField(
        help_text="File size in bytes. Must be > 0.",
    )
    sha256 = models.CharField(
        max_length=64,
        help_text="SHA-256 cryptographic hash (64 lowercase hex characters).",
    )
    storage_key = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        help_text="Secret unguessable random storage key (64 hex characters). Never exposed by API.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text="Lifecycle status: active, archived, or deleted.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when document was uploaded.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of last metadata update.",
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when document was archived.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when document was soft-deleted.",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deleted_documents",
        help_text="User who initiated soft deletion.",
    )
    purged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when physical file bytes were destroyed from storage.",
    )

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(size__gt=0),
                name="document_size_positive",
            ),
            models.CheckConstraint(
                check=models.Q(file_type__in=["PDF", "DOCX", "XLSX", "PPTX"]),
                name="document_valid_file_type",
            ),
            models.CheckConstraint(
                check=models.Q(status__in=["active", "archived", "deleted"]),
                name="document_valid_status",
            ),
            models.CheckConstraint(
                check=models.Q(sha256__regex=r"^[0-9a-f]{64}$"),
                name="document_sha256_format",
            ),
            models.CheckConstraint(
                check=models.Q(storage_key__regex=r"^[0-9a-f]{64}$"),
                name="document_storage_key_format",
            ),
            models.UniqueConstraint(
                functions.Lower("name"),
                "owner",
                condition=models.Q(status__in=["active", "archived"]),
                name="unique_active_archived_document_owner_name",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "status", "-created_at"], name="doc_owner_status_created_idx"),
            models.Index(fields=["owner", "folder"], name="doc_owner_folder_idx"),
            models.Index(fields=["sha256"], name="doc_sha256_idx"),
        ]

    def clean(self):
        super().clean()
        if self.folder_id and self.owner_id:
            try:
                if self.folder.owner_id != self.owner_id:
                    raise ValidationError(
                        {"folder": "Document and folder must belong to the same owner."}
                    )
            except Folder.DoesNotExist:
                raise ValidationError({"folder": "Referenced folder does not exist."})

    def save(self, *args, **kwargs):
        if self.folder_id and self.owner_id:
            try:
                if self.folder.owner_id != self.owner_id:
                    raise ValidationError(
                        "Document and folder must belong to the same owner."
                    )
            except Folder.DoesNotExist:
                raise ValidationError("Referenced folder does not exist.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.status}) [Owner: {self.owner_id}]"


class DocumentShare(models.Model):
    """A time-bound, document-level grant made by a document owner."""

    class Permission(models.TextChoices):
        VIEW = "VIEW", "View"
        DOWNLOAD = "DOWNLOAD", "Download"
        EDIT = "EDIT", "Edit"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_shares_received",
    )
    permission = models.CharField(max_length=10, choices=Permission.choices)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "recipient"],
                name="unique_document_share_recipient",
            ),
        ]
        indexes = [
            models.Index(fields=["recipient", "-created_at"], name="share_recipient_created_idx"),
        ]

    @property
    def is_active(self):
        from django.utils import timezone
        return self.expires_at is None or self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.document_id} shared with {self.recipient_id} ({self.permission})"


class EmployeeNotification(models.Model):
    """A persisted, per-employee inbox item for document-related events."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_notifications",
    )
    document = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    message = models.CharField(max_length=300)
    event_key = models.CharField(
        max_length=120,
        unique=True,
        help_text="Stable idempotency key for system-generated notifications.",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"], name="employee_notice_inbox_idx"),
        ]

    def __str__(self):
        return f"Notification for {self.recipient_id}: {self.message[:60]}"
