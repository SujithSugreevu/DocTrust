"""
Views for DocTrust folder and document management.

Security design:
- All endpoints require IsAuthenticated + IsActiveUser + IsEmployee.
- ADMIN accounts are explicitly denied (IsEmployee rejects non-EMPLOYEE roles).
- Non-owned resources always return 404 to prevent enumeration.
- Uploaded files are validated (magic bytes, PDF active-content, Office ZIP security)
  before any bytes are written to storage.
- File bytes are written to PrivateDocumentStorage first; database insertion happens
  inside transaction.atomic(). If the DB write fails, the stored file is explicitly
  deleted to prevent orphaned files.
- Storage keys are never returned in API responses.
- Download is handled via a streaming FileResponse with a content-disposition header.
"""

import hashlib
import logging
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsActiveUser
from auditlog.helpers import log_event
from auditlog.models import AuditEvent
from documents.models import Document, Folder
from documents.permissions import IsEmployee
from documents.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentMetadataUpdateSerializer,
    DocumentUploadSerializer,
    FolderSerializer,
)
from documents.storage import PrivateDocumentStorage, StorageError, get_user_storage_usage
from documents.validators import sanitize_filename, validate_document_upload

logger = logging.getLogger("documents")

_EMPLOYEE_PERMISSIONS = [IsAuthenticated, IsActiveUser, IsEmployee]


# ──────────────────────────────────────────────────────────────────────────────
# Folder endpoints
# ──────────────────────────────────────────────────────────────────────────────


class FolderListCreateView(APIView):
    """
    GET  /api/documents/folders/         — list caller's folders
    POST /api/documents/folders/         — create a folder
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        folders = (
            Folder.objects.filter(owner=request.user)
            .annotate(
                document_count=Count(
                    "documents",
                    filter=Q(documents__status__in=[Document.Status.ACTIVE, Document.Status.ARCHIVED]),
                )
            )
            .order_by("name")
        )
        serializer = FolderSerializer(folders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = FolderSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            folder = serializer.save()
            log_event(
                actor=request.user,
                action=AuditEvent.Action.FOLDER_CREATE,
                target=folder,
                request=request,
                fail_closed=True,
            )

        return Response(
            FolderSerializer(folder).data,
            status=status.HTTP_201_CREATED,
        )


class FolderDetailView(APIView):
    """
    GET    /api/documents/folders/<uuid:pk>/  — retrieve folder detail
    PATCH  /api/documents/folders/<uuid:pk>/  — rename folder
    DELETE /api/documents/folders/<uuid:pk>/  — delete empty folder
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def _get_folder(self, pk, user):
        folder = Folder.objects.filter(owner=user, pk=pk).first()
        if not folder:
            raise Http404
        return folder

    def get(self, request, pk):
        folder = self._get_folder(pk, request.user)
        serializer = FolderSerializer(
            Folder.objects.annotate(
                document_count=Count(
                    "documents",
                    filter=Q(documents__status__in=[Document.Status.ACTIVE, Document.Status.ARCHIVED]),
                )
            ).get(pk=folder.pk)
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        folder = self._get_folder(pk, request.user)
        serializer = FolderSerializer(
            folder,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            folder = serializer.save()
            log_event(
                actor=request.user,
                action=AuditEvent.Action.FOLDER_RENAME,
                target=folder,
                request=request,
                fail_closed=True,
            )

        return Response(FolderSerializer(folder).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        folder = self._get_folder(pk, request.user)

        # Enforce empty-folder invariant
        if folder.documents.exists():
            return Response(
                {"detail": "Cannot delete folder because it still contains documents."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            log_event(
                actor=request.user,
                action=AuditEvent.Action.FOLDER_DELETE,
                target=folder,
                request=request,
                fail_closed=True,
            )
            folder.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────────────────────
# Document endpoints
# ──────────────────────────────────────────────────────────────────────────────


class DocumentListCreateView(APIView):
    """
    GET  /api/documents/           — list caller's documents (filterable)
    POST /api/documents/           — upload a new document (multipart/form-data)
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        qs = Document.objects.filter(owner=request.user)

        # Status filter (default: active only)
        status_param = request.query_params.get("status", "active")
        if status_param == "all":
            pass  # return all statuses
        elif status_param in [Document.Status.ACTIVE, Document.Status.ARCHIVED, Document.Status.DELETED]:
            qs = qs.filter(status=status_param)
        else:
            qs = qs.filter(status=Document.Status.ACTIVE)

        # Full-text search on name/description
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        # Folder filter
        folder_id = request.query_params.get("folder", "").strip()
        if folder_id == "none":
            qs = qs.filter(folder__isnull=True)
        elif folder_id:
            qs = qs.filter(folder__id=folder_id, folder__owner=request.user)

        # File type filter
        file_type = request.query_params.get("file_type", "").strip().upper()
        if file_type in [ft for ft, _ in Document.FileType.choices]:
            qs = qs.filter(file_type=file_type)

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        allowed_orderings = {
            "name", "-name",
            "created_at", "-created_at",
            "updated_at", "-updated_at",
            "size", "-size",
        }
        if ordering not in allowed_orderings:
            ordering = "-created_at"
        qs = qs.order_by(ordering)

        # Pagination
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        page = max(int(request.query_params.get("page", 1)), 1)
        total = qs.count()
        documents = qs[(page - 1) * page_size: page * page_size]

        serializer = DocumentListSerializer(documents, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["file"]
        raw_filename = uploaded_file.name or ""
        folder_obj = serializer.validated_data.get("folder")
        description = serializer.validated_data.get("description", "")

        # ── Security validation ───────────────────────────────────────
        try:
            file_type, content_type, file_bytes = validate_document_upload(
                uploaded_file, raw_filename
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.message if hasattr(exc, "message") else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Quota check ───────────────────────────────────────────────
        quota_bytes = getattr(settings, "USER_STORAGE_QUOTA_BYTES", 500 * 1024 * 1024)
        current_usage = get_user_storage_usage(request.user)
        if current_usage + len(file_bytes) > quota_bytes:
            return Response(
                {"detail": "Storage quota exceeded. Delete or purge documents before uploading more."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Derive metadata ───────────────────────────────────────────
        safe_filename = sanitize_filename(raw_filename)
        name_input = serializer.validated_data.get("name", "").strip()
        doc_name = name_input if name_input else safe_filename

        sha256 = hashlib.sha256(file_bytes).hexdigest()
        storage = PrivateDocumentStorage()
        storage_key = storage.generate_storage_key()

        # ── Write to private storage ──────────────────────────────────
        try:
            storage.save_stream(BytesIO(file_bytes), storage_key)
        except StorageError as exc:
            logger.error("Storage write failed for user %s: %s", request.user.pk, exc)
            return Response(
                {"detail": "File storage failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Persist metadata in database ──────────────────────────────
        document = None
        try:
            with transaction.atomic():
                document = Document.objects.create(
                    owner=request.user,
                    folder=folder_obj,
                    name=doc_name,
                    original_filename=safe_filename,
                    description=description,
                    file_type=file_type,
                    size=len(file_bytes),
                    sha256=sha256,
                    storage_key=storage_key,
                    status=Document.Status.ACTIVE,
                )
                log_event(
                    actor=request.user,
                    action=AuditEvent.Action.DOCUMENT_UPLOAD,
                    target=document,
                    request=request,
                    metadata={
                        "file_size": len(file_bytes),
                        "content_type": content_type,
                        "sha256": sha256,
                        "file_extension": f".{file_type.lower()}",
                    },
                    fail_closed=True,
                )
        except Exception as exc:
            # DB write or audit logging failed — clean up stored file to prevent orphans
            logger.error(
                "Document DB insert failed for user %s (storage_key=%s): %s",
                request.user.pk,
                storage_key,
                exc,
            )
            try:
                storage.delete(storage_key)
            except StorageError as cleanup_err:
                logger.critical(
                    "ORPHANED FILE: storage cleanup failed after DB error for key=%s: %s",
                    storage_key,
                    cleanup_err,
                )
            return Response(
                {"detail": "Upload failed during processing. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            DocumentDetailSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(APIView):
    """
    GET    /api/documents/<uuid:pk>/   — retrieve document metadata
    PATCH  /api/documents/<uuid:pk>/   — update name, description, or folder
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def _get_document(self, pk, user, include_deleted=False):
        qs = Document.objects.filter(owner=user, pk=pk)
        if not include_deleted:
            qs = qs.exclude(status=Document.Status.DELETED)
        doc = qs.first()
        if not doc:
            raise Http404
        return doc

    def get(self, request, pk):
        doc = self._get_document(pk, request.user)
        log_event(
            actor=request.user,
            action=AuditEvent.Action.DOCUMENT_VIEW,
            target=doc,
            request=request,
            fail_closed=False,
        )
        return Response(DocumentDetailSerializer(doc).data)

    def patch(self, request, pk):
        doc = self._get_document(pk, request.user)
        if doc.status == Document.Status.DELETED:
            return Response(
                {"detail": "Cannot update a deleted document."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentMetadataUpdateSerializer(
            doc, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            doc = serializer.save()
            log_event(
                actor=request.user,
                action=AuditEvent.Action.DOCUMENT_UPDATE,
                target=doc,
                request=request,
                fail_closed=True,
            )

        return Response(DocumentDetailSerializer(doc).data)

    def delete(self, request, pk):
        return DocumentDeleteView().delete(request, pk)


class DocumentDownloadView(APIView):
    """
    GET /api/documents/<uuid:pk>/download/

    Streams the physical file bytes to the authenticated owner.
    Never exposes the storage key. Validates file existence on disk
    before streaming. Records a DOCUMENT_DOWNLOAD audit event.
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request, pk):
        doc = Document.objects.filter(
            owner=request.user,
            pk=pk,
            status=Document.Status.ACTIVE,
        ).first()
        if not doc:
            raise Http404

        storage = PrivateDocumentStorage()
        if not storage.exists(doc.storage_key):
            logger.error(
                "Storage file missing for document pk=%s storage_key=%s",
                doc.pk,
                doc.storage_key,
            )
            return Response(
                {"detail": "Document file is not available. Please contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        log_event(
            actor=request.user,
            action=AuditEvent.Action.DOCUMENT_DOWNLOAD,
            target=doc,
            request=request,
            metadata={
                "file_size": doc.size,
                "content_type": _file_type_to_mime(doc.file_type),
                "sha256": doc.sha256,
            },
            fail_closed=False,
        )

        file_handle = storage.open(doc.storage_key)
        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=doc.name,
            content_type=_file_type_to_mime(doc.file_type),
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Disposition"] = (
            f'attachment; filename="{doc.name}"'
        )
        return response


class DocumentArchiveView(APIView):
    """
    POST /api/documents/<uuid:pk>/archive/  — archive an active document
    POST /api/documents/<uuid:pk>/restore/  — restore an archived document to active
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def post(self, request, pk, action):
        doc = Document.objects.filter(owner=request.user, pk=pk).first()
        if not doc:
            raise Http404

        if action == "archive":
            if doc.status != Document.Status.ACTIVE:
                return Response(
                    {"detail": "Only active documents can be archived."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                doc.status = Document.Status.ARCHIVED
                doc.archived_at = timezone.now()
                doc.save(update_fields=["status", "archived_at", "updated_at"])
                log_event(
                    actor=request.user,
                    action=AuditEvent.Action.DOCUMENT_ARCHIVE,
                    target=doc,
                    request=request,
                    fail_closed=True,
                )
            return Response(DocumentDetailSerializer(doc).data)

        elif action == "restore":
            if doc.status != Document.Status.ARCHIVED:
                return Response(
                    {"detail": "Only archived documents can be restored."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                doc.status = Document.Status.ACTIVE
                doc.archived_at = None
                doc.save(update_fields=["status", "archived_at", "updated_at"])
                log_event(
                    actor=request.user,
                    action=AuditEvent.Action.DOCUMENT_RESTORE,
                    target=doc,
                    request=request,
                    fail_closed=True,
                )
            return Response(DocumentDetailSerializer(doc).data)

        return Response({"detail": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)


class DocumentDeleteView(APIView):
    """
    DELETE /api/documents/<uuid:pk>/   — soft-delete an active/archived document

    Soft-deletion records deleted_at and deleted_by, sets status=deleted.
    Physical file bytes remain until an explicit purge.
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def delete(self, request, pk):
        doc = Document.objects.filter(
            owner=request.user,
            pk=pk,
        ).exclude(status=Document.Status.DELETED).first()
        if not doc:
            raise Http404

        with transaction.atomic():
            doc.status = Document.Status.DELETED
            doc.deleted_at = timezone.now()
            doc.deleted_by = request.user
            doc.save(update_fields=["status", "deleted_at", "deleted_by", "updated_at"])
            log_event(
                actor=request.user,
                action=AuditEvent.Action.DOCUMENT_DELETE,
                target=doc,
                request=request,
                fail_closed=True,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentPurgeView(APIView):
    """
    POST /api/documents/<uuid:pk>/purge/

    Permanently destroys the physical file bytes from storage and marks
    the document record as purged. The metadata record is retained for
    the audit trail. Only deleted documents may be purged.
    """
    permission_classes = _EMPLOYEE_PERMISSIONS

    def post(self, request, pk):
        doc = Document.objects.filter(
            owner=request.user,
            pk=pk,
            status=Document.Status.DELETED,
        ).first()
        if not doc:
            raise Http404

        if doc.purged_at is not None:
            return Response(
                {"detail": "This document has already been purged."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        storage = PrivateDocumentStorage()
        storage_key = doc.storage_key

        # Destroy physical file first; if this fails, abort without touching the DB.
        try:
            storage.delete(storage_key)
        except StorageError as exc:
            logger.error("Purge storage delete failed for document pk=%s: %s", pk, exc)
            return Response(
                {"detail": "File purge failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Record purge in DB
        try:
            with transaction.atomic():
                doc.purged_at = timezone.now()
                doc.save(update_fields=["purged_at", "updated_at"])
                log_event(
                    actor=request.user,
                    action=AuditEvent.Action.DOCUMENT_PURGE,
                    target=doc,
                    request=request,
                    fail_closed=True,
                )
        except Exception as exc:
            # Physical file is already deleted. Log inconsistency but do not re-raise
            # since exposing this error to the user would be misleading.
            logger.critical(
                "PURGE INCONSISTENCY: file deleted but DB update failed for pk=%s key=%s: %s",
                pk,
                storage_key,
                exc,
            )
            return Response(
                {"detail": "Purge recorded but database update failed. Please contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_MIME_MAP = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _file_type_to_mime(file_type: str) -> str:
    return _MIME_MAP.get(file_type, "application/octet-stream")
