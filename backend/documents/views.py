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
from doctrust.startup import format_safe_exception
from documents.models import Document, DocumentShare, EmployeeNotification, Folder
from documents.permissions import IsEmployee
from documents.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentMetadataUpdateSerializer,
    DocumentShareSerializer,
    DocumentShareWriteSerializer,
    DocumentUploadSerializer,
    EmployeeNotificationSerializer,
    FolderSerializer,
)
from documents.storage import PrivateDocumentStorage, StorageError, get_user_storage_usage
from documents.validators import sanitize_filename, validate_document_upload

logger = logging.getLogger("documents")

_EMPLOYEE_PERMISSIONS = [IsAuthenticated, IsActiveUser, IsEmployee]


def _active_share(document, user):
    """Return a current grant for user, without leaking whether any other grant exists."""
    return document.shares.filter(
        recipient=user,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).first()


def _can_access(document, user):
    return document.owner_id == user.id or _active_share(document, user)


def _can_download(document, user):
    if document.owner_id == user.id:
        return True
    share = _active_share(document, user)
    return bool(share and share.permission in {
        DocumentShare.Permission.DOWNLOAD,
        DocumentShare.Permission.EDIT,
    })


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
        # Dynamically load per-user quota from system settings
        try:
            from systemsettings.services import get_system_settings
            sys_settings = get_system_settings()
            quota_bytes = sys_settings.user_storage_quota_mb * 1024 * 1024
        except Exception:
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
            logger.error(
                "Storage write failed for user %s:\n%s",
                request.user.pk,
                format_safe_exception(exc),
            )
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
                "Document DB insert failed for user %s:\n%s",
                request.user.pk,
                format_safe_exception(exc),
            )
            try:
                storage.delete(storage_key)
            except StorageError as cleanup_err:
                logger.critical(
                    "ORPHANED FILE: storage cleanup failed after DB error for user %s:\n%s",
                    request.user.pk,
                    format_safe_exception(cleanup_err),
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
        qs = Document.objects.filter(pk=pk)
        if not include_deleted:
            qs = qs.exclude(status=Document.Status.DELETED)
        doc = qs.first()
        if not doc or not _can_access(doc, user):
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

        share = _active_share(doc, request.user)
        if doc.owner_id != request.user.id and (not share or share.permission != DocumentShare.Permission.EDIT):
            return Response({"detail": "Edit permission is required to update this document."}, status=status.HTTP_403_FORBIDDEN)
        # A recipient with edit access may correct title/description but cannot reorganize another owner's files.
        if doc.owner_id != request.user.id and "folder" in request.data:
            return Response({"detail": "Only the owner can move a shared document."}, status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentMetadataUpdateSerializer(
            doc, data=request.data, partial=True, context={"request": request, "owner": doc.owner}
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
        doc = Document.objects.filter(pk=pk, status=Document.Status.ACTIVE).first()
        if not doc or not _can_download(doc, request.user):
            raise Http404

        storage = PrivateDocumentStorage()
        if not storage.exists(doc.storage_key):
            logger.error(
                "Storage file missing for document pk=%s",
                doc.pk,
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


class DocumentViewFileView(APIView):
    """Secure inline original-file view for browser-previewable documents."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request, pk):
        doc = Document.objects.filter(pk=pk, status=Document.Status.ACTIVE).first()
        if not doc or not _can_access(doc, request.user):
            raise Http404
        storage = PrivateDocumentStorage()
        if not storage.exists(doc.storage_key):
            logger.error("Storage file missing for inline view pk=%s", pk)
            return Response({"detail": "Document file is not available. Please contact support."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        log_event(actor=request.user, action=AuditEvent.Action.DOCUMENT_VIEW, target=doc, request=request, fail_closed=False)
        response = FileResponse(storage.open(doc.storage_key), as_attachment=False, filename=doc.name, content_type=_file_type_to_mime(doc.file_type))
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Disposition"] = f'inline; filename="{doc.name}"'
        return response


class DocumentStorageUsageView(APIView):
    """Return only the caller's quota allocation and current active/archive usage."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        try:
            from systemsettings.services import get_system_settings
            quota = get_system_settings().user_storage_quota_mb * 1024 * 1024
        except Exception:
            quota = settings.USER_STORAGE_QUOTA_BYTES
        used = get_user_storage_usage(request.user)
        return Response({"used_bytes": used, "quota_bytes": quota, "remaining_bytes": max(0, quota - used)})


class ShareRecipientListView(APIView):
    """List active employee accounts suitable for a share recipient picker."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        from accounts.models import User
        users = User.objects.filter(
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
            is_active=True,
        ).exclude(pk=request.user.pk).order_by("username")
        return Response([
            {"id": user.id, "username": user.username, "display_name": user.get_full_name() or user.username, "email": user.email}
            for user in users
        ])


class EmployeeDocumentActivityView(APIView):
    """Return the caller's persisted audit events, never another employee's history."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        events = AuditEvent.objects.filter(actor=request.user).order_by("-timestamp")[:100]
        document_ids = [
            event.target_id
            for event in events
            if (event.target_type or "").lower() == "documents.document" and event.target_id
        ]
        document_names = {
            str(doc.id): doc.name
            for doc in Document.objects.filter(id__in=document_ids)
        }
        return Response({"results": [
            {
                "id": event.id,
                "action": event.action,
                "action_label": event.get_action_display(),
                "timestamp": event.timestamp,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "document_name": document_names.get(event.target_id),
                "outcome": "Failed" if event.action in {AuditEvent.Action.LOGIN_FAILED, AuditEvent.Action.MFA_LOGIN_FAILED} else "Success",
            }
            for event in events
        ]})


class EmployeeNotificationListView(APIView):
    """Return only the authenticated employee's persisted notifications."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        notifications = EmployeeNotification.objects.filter(recipient=request.user).select_related("document")[:100]
        return Response({"results": EmployeeNotificationSerializer(notifications, many=True).data})


class EmployeeNotificationReadView(APIView):
    """Mark one inbox item as read without exposing another employee's items."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def post(self, request, pk):
        notification = EmployeeNotification.objects.filter(pk=pk, recipient=request.user).first()
        if not notification:
            raise Http404
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(EmployeeNotificationSerializer(notification).data)


class EmployeeNotificationReadAllView(APIView):
    """Mark the caller's unread inbox items as read."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def post(self, request):
        EmployeeNotification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SharedDocumentListView(APIView):
    """List documents granted to the caller by another active employee."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        shares = DocumentShare.objects.select_related("document", "document__owner").filter(
            recipient=request.user,
            document__status=Document.Status.ACTIVE,
        ).exclude(document__owner=request.user).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        results = []
        for share in shares:
            data = DocumentListSerializer(share.document).data
            data.update({
                "owner_name": share.document.owner.get_full_name() or share.document.owner.username,
                "owner_username": share.document.owner.username,
                "owner_email": share.document.owner.email,
                "shared_at": share.created_at,
                "permission": share.permission,
                "expires_at": share.expires_at,
                "share_id": share.id,
            })
            results.append(data)
        return Response({"count": len(results), "results": results})


class OwnedDocumentShareListView(APIView):
    """List the caller's grants in one request for the Employee workspace."""
    permission_classes = _EMPLOYEE_PERMISSIONS

    def get(self, request):
        shares = DocumentShare.objects.filter(
            document__owner=request.user,
            document__status=Document.Status.ACTIVE,
        ).exclude(
            recipient=request.user,
        ).select_related("document", "recipient").order_by("-created_at")
        return Response(DocumentShareSerializer(shares, many=True).data)


class DocumentShareListCreateView(APIView):
    permission_classes = _EMPLOYEE_PERMISSIONS

    def _get_document(self, pk, user):
        doc = Document.objects.filter(pk=pk, status=Document.Status.ACTIVE).first()
        if not doc or not _can_access(doc, user):
            raise Http404
        return doc

    def _get_owned_document(self, pk, user):
        doc = Document.objects.filter(pk=pk, owner=user, status=Document.Status.ACTIVE).first()
        if not doc:
            raise Http404
        return doc

    def get(self, request, pk):
        doc = self._get_document(pk, request.user)
        # Self-shares are rejected on creation. Exclude any legacy records so
        # they cannot be reported as an active grant after a safe ownership
        # migration of demonstration data.
        shares = doc.shares.exclude(recipient=doc.owner).select_related("recipient")
        return Response(DocumentShareSerializer(shares, many=True).data)

    def post(self, request, pk):
        doc = self._get_owned_document(pk, request.user)
        serializer = DocumentShareWriteSerializer(data=request.data, context={"document": doc})
        if not serializer.is_valid():
            return Response({"detail": "Invalid share.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        with transaction.atomic():
            share, created = DocumentShare.objects.update_or_create(
                document=doc,
                recipient=data["recipient"],
                defaults={"permission": data["permission"], "expires_at": data.get("expires_at")},
            )
            EmployeeNotification.objects.update_or_create(
                event_key=f"share:{doc.id}:{share.recipient_id}",
                defaults={
                    "recipient": share.recipient,
                    "document": doc,
                    "message": f"{request.user.get_full_name() or request.user.username} shared {doc.name} with you ({share.get_permission_display()}).",
                    "is_read": False,
                    "read_at": None,
                },
            )
            log_event(actor=request.user, action=AuditEvent.Action.DOCUMENT_SHARE if created else AuditEvent.Action.DOCUMENT_SHARE_UPDATE, target=doc, request=request, metadata={"status": share.permission}, fail_closed=True)
        return Response(DocumentShareSerializer(share).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DocumentShareDetailView(DocumentShareListCreateView):
    def _get_share(self, pk, share_id, user):
        doc = self._get_owned_document(pk, user)
        share = doc.shares.filter(pk=share_id).select_related("recipient").first()
        if not share:
            raise Http404
        return doc, share

    def patch(self, request, pk, share_id):
        doc, share = self._get_share(pk, share_id, request.user)
        serializer = DocumentShareWriteSerializer(data={**request.data, "recipient": share.recipient_id}, partial=True, context={"document": doc})
        if not serializer.is_valid():
            return Response({"detail": "Invalid share.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            share.permission = serializer.validated_data.get("permission", share.permission)
            share.expires_at = serializer.validated_data.get("expires_at", share.expires_at)
            share.save(update_fields=["permission", "expires_at", "updated_at"])
            EmployeeNotification.objects.update_or_create(
                event_key=f"share:{doc.id}:{share.recipient_id}",
                defaults={
                    "recipient": share.recipient,
                    "document": doc,
                    "message": f"Access to {doc.name} was updated to {share.get_permission_display()}.",
                    "is_read": False,
                    "read_at": None,
                },
            )
            log_event(actor=request.user, action=AuditEvent.Action.DOCUMENT_SHARE_UPDATE, target=doc, request=request, metadata={"status": share.permission}, fail_closed=True)
        return Response(DocumentShareSerializer(share).data)

    def delete(self, request, pk, share_id):
        doc, share = self._get_share(pk, share_id, request.user)
        with transaction.atomic():
            recipient = share.recipient
            share.delete()
            EmployeeNotification.objects.update_or_create(
                event_key=f"share-revoked:{doc.id}:{recipient.id}",
                defaults={
                    "recipient": recipient,
                    "document": doc,
                    "message": f"Your access to {doc.name} was revoked.",
                    "is_read": False,
                    "read_at": None,
                },
            )
            log_event(actor=request.user, action=AuditEvent.Action.DOCUMENT_SHARE_REVOKE, target=doc, request=request, fail_closed=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
            logger.error(
                "Purge storage delete failed for document pk=%s:\n%s",
                pk,
                format_safe_exception(exc),
            )
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
                "PURGE INCONSISTENCY: file deleted but DB update failed for pk=%s:\n%s",
                pk,
                format_safe_exception(exc),
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
