"""
Serializers for DocTrust folders and documents.
"""

import hashlib

from rest_framework import serializers

from accounts.models import User
from documents.models import Document, DocumentShare, EmployeeNotification, Folder


class FolderSerializer(serializers.ModelSerializer):
    """
    Serializer for listing, creating, and renaming folders.
    Enforces per-owner case-insensitive uniqueness and non-blank names.
    """
    document_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "created_at",
            "document_count",
        ]
        read_only_fields = ["id", "created_at", "document_count"]

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Folder name cannot be blank.")
        if len(name) > 40:
            raise serializers.ValidationError("Folder name cannot exceed 40 characters.")

        # Per-owner case-insensitive uniqueness check
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            qs = Folder.objects.filter(owner=request.user, name__iexact=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A folder with this name already exists.")

        return name

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for document list views.
    Never exposes storage_key, sha256 is included for integrity verification display.
    """
    folder_name = serializers.SerializerMethodField()
    size_display = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "name",
            "description",
            "file_type",
            "size",
            "size_display",
            "status",
            "folder",
            "folder_name",
            "created_at",
            "updated_at",
            "archived_at",
            "deleted_at",
        ]
        read_only_fields = fields

    def get_folder_name(self, obj):
        return obj.folder.name if obj.folder else None

    def get_size_display(self, obj):
        size = obj.size
        if size < 1024 * 1024:
            return f"{max(1, round(size / 1024))} KB"
        return f"{size / (1024 * 1024):.1f} MB"


class DocumentDetailSerializer(DocumentListSerializer):
    """
    Full detail serializer, still excludes storage_key.
    sha256 is exposed for integrity verification purposes (non-sensitive).
    """
    class Meta(DocumentListSerializer.Meta):
        fields = DocumentListSerializer.Meta.fields + [
            "original_filename",
            "sha256",
            "purged_at",
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    """
    Handles upload form data. Validation of file content happens
    in the view using validate_document_upload() from validators.py.
    """
    file = serializers.FileField(write_only=True)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    folder = serializers.UUIDField(required=False, allow_null=True)

    def validate_name(self, value):
        return value.strip()

    def validate_folder(self, value):
        if value is None:
            return None
        request = self.context.get("request")
        try:
            folder = Folder.objects.get(pk=value, owner=request.user)
        except Folder.DoesNotExist:
            raise serializers.ValidationError("Folder not found or does not belong to you.")
        return folder


class DocumentMetadataUpdateSerializer(serializers.ModelSerializer):
    """
    Allows updating name, description, and folder assignment.
    All other fields are immutable after upload.
    """
    folder = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Document
        fields = ["name", "description", "folder"]

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Document name cannot be blank.")
        if len(name) > 100:
            raise serializers.ValidationError("Document name cannot exceed 100 characters.")
        # Per-owner case-insensitive uniqueness for active/archived documents
        request = self.context.get("request")
        owner = self.context.get("owner", request.user if request else None)
        if owner and owner.is_authenticated:
            qs = Document.objects.filter(
                owner=owner,
                name__iexact=name,
                status__in=[Document.Status.ACTIVE, Document.Status.ARCHIVED],
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "A document with this name already exists in your active documents."
                )
        return name

    def validate_folder(self, value):
        if value is None:
            return None
        request = self.context.get("request")
        owner = self.context.get("owner", request.user if request else None)
        try:
            folder = Folder.objects.get(pk=value, owner=owner)
        except Folder.DoesNotExist:
            raise serializers.ValidationError("Folder not found or does not belong to you.")
        return folder

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        if "folder" in validated_data:
            instance.folder = validated_data["folder"]
        instance.save()
        return instance


class DocumentShareSerializer(serializers.ModelSerializer):
    """Safe share representation; never exposes a recipient's private fields."""

    recipient_username = serializers.CharField(source="recipient.username", read_only=True)
    recipient_name = serializers.SerializerMethodField()
    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)

    class Meta:
        model = DocumentShare
        fields = [
            "id", "document", "recipient", "recipient_username", "recipient_name",
            "recipient_email", "permission", "expires_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "document", "recipient_username", "recipient_name", "recipient_email", "created_at", "updated_at"]

    def get_recipient_name(self, obj):
        return obj.recipient.get_full_name() or obj.recipient.username


class DocumentShareWriteSerializer(serializers.Serializer):
    recipient = serializers.IntegerField(required=True)
    permission = serializers.ChoiceField(choices=DocumentShare.Permission.choices)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_recipient(self, value):
        try:
            user = User.objects.get(pk=value, role=User.Role.EMPLOYEE, status=User.Status.ACTIVE, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient must be an active employee.")
        document = self.context["document"]
        if user.pk == document.owner_id:
            raise serializers.ValidationError("You cannot share a document with its owner.")
        return user

    def validate_expires_at(self, value):
        from django.utils import timezone
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("Expiry must be in the future.")
        return value


class EmployeeNotificationSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(source="document.id", read_only=True, allow_null=True)

    class Meta:
        model = EmployeeNotification
        fields = ["id", "document_id", "message", "is_read", "created_at", "read_at"]
        read_only_fields = fields
