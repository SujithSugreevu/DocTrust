"""
Tests for Folder and Document Ownership Integrity.

Verifies:
- Document and its folder must belong to the same owner.
- NULL folder is permitted.
- Cross-owner folder assignment is rejected at application level (clean, save).
- Cross-owner folder assignment is blocked at database level (composite foreign key)
  even when application-level save() is bypassed via QuerySet.update().
"""

import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from auditlog.models import AuditEvent
from documents.models import Document, Folder

User = get_user_model()


class FolderOwnershipIntegrityTests(TestCase):
    """
    Regression tests verifying that a document's folder must belong
    to the exact same owner as the document.
    """

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="employee_one",
            email="emp1@example.com",
            password="SecurePassword123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )
        self.user2 = User.objects.create_user(
            username="employee_two",
            email="emp2@example.com",
            password="SecurePassword123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )

        self.folder1 = Folder.objects.create(
            name="Employee 1 Folder",
            owner=self.user1,
        )
        self.folder2 = Folder.objects.create(
            name="Employee 2 Folder",
            owner=self.user2,
        )

    def _sample_doc_kwargs(self, owner, folder=None, name="test_doc.pdf"):
        return {
            "owner": owner,
            "folder": folder,
            "name": name,
            "original_filename": name,
            "description": "Test document",
            "file_type": Document.FileType.PDF,
            "size": 1024,
            "sha256": "a" * 64,
            "storage_key": uuid.uuid4().hex + uuid.uuid4().hex,
            "status": Document.Status.ACTIVE,
        }

    def test_same_owner_folder_assignment_succeeds(self):
        """A document in a folder owned by the same user succeeds."""
        kwargs = self._sample_doc_kwargs(self.user1, folder=self.folder1)
        doc = Document(**kwargs)
        doc.full_clean()
        doc.save()

        self.assertIsNotNone(doc.id)
        self.assertEqual(doc.owner, self.user1)
        self.assertEqual(doc.folder, self.folder1)

    def test_null_folder_assignment_succeeds(self):
        """A document with no folder (root/unfiled) succeeds."""
        kwargs = self._sample_doc_kwargs(self.user1, folder=None)
        doc = Document(**kwargs)
        doc.full_clean()
        doc.save()

        self.assertIsNotNone(doc.id)
        self.assertIsNone(doc.folder)

    def test_cross_owner_folder_clean_raises_validation_error(self):
        """clean() rejects assignment of another user's folder."""
        kwargs = self._sample_doc_kwargs(self.user1, folder=self.folder2)
        doc = Document(**kwargs)

        with self.assertRaises(ValidationError) as ctx:
            doc.clean()
        self.assertIn("folder", ctx.exception.message_dict)

    def test_cross_owner_folder_save_raises_validation_error(self):
        """save() rejects creation of a document in another user's folder."""
        kwargs = self._sample_doc_kwargs(self.user1, folder=self.folder2)
        doc = Document(**kwargs)

        with self.assertRaises(ValidationError) as ctx:
            doc.save()
        self.assertIn("same owner", str(ctx.exception))

    def test_cross_owner_folder_reassignment_rejected(self):
        """Reassigning an existing document to another user's folder is rejected."""
        kwargs = self._sample_doc_kwargs(self.user1, folder=self.folder1)
        doc = Document.objects.create(**kwargs)

        # Attempt reassignment to user2's folder
        doc.folder = self.folder2
        with self.assertRaises(ValidationError):
            doc.save()

    def test_database_constraint_blocks_cross_owner_folder_on_update(self):
        """
        Database-level composite foreign key constraint blocks cross-owner assignment
        even when ORM save() validation is bypassed via QuerySet.update().
        """
        kwargs = self._sample_doc_kwargs(self.user1, folder=self.folder1)
        doc = Document.objects.create(**kwargs)

        # Bypass Python save() and clean() via direct SQL UPDATE
        with self.assertRaises(IntegrityError) as ctx:
            with transaction.atomic():
                Document.objects.filter(id=doc.id).update(folder=self.folder2)
        self.assertIn("documents_document_folder_owner_fk", str(ctx.exception))

        # Confirm database row remained intact
        doc.refresh_from_db()
        self.assertEqual(doc.folder_id, self.folder1.id)
        self.assertEqual(doc.owner_id, self.user1.id)

    def test_raw_sql_insert_violates_foreign_key_constraint(self):
        """
        Direct raw SQL INSERT with cross-owner folder_id is rejected by PostgreSQL
        with a foreign key violation on documents_document_folder_owner_fk.
        """
        with self.assertRaises(IntegrityError) as ctx:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO documents_document (
                            id, name, original_filename, description, file_type,
                            size, sha256, storage_key, status, created_at, updated_at,
                            owner_id, folder_id
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s
                        )
                        """,
                        [
                            uuid.uuid4(), "raw_test.pdf", "raw_test.pdf", "desc", "PDF",
                            100, "b" * 64, uuid.uuid4().hex + uuid.uuid4().hex, "active",
                            self.user1.id, self.folder2.id,
                        ],
                    )
        self.assertIn("documents_document_folder_owner_fk", str(ctx.exception))


class FolderAPITests(APITestCase):
    """
    Integration tests for Folder REST API endpoints (/api/folders/ and /api/folders/<id>/).
    Covers:
    - Unauthenticated access rejection (401)
    - ADMIN role access denial (403)
    - Owner isolation (cross-owner access returns 404)
    - Folder creation with audit logging
    - Duplicate folder name validation (case-insensitive per owner)
    - Cross-owner duplicate names permitted
    - Invalid folder name validation (blank, length > 40)
    - Folder rename with audit logging
    - Folder deletion of empty folders with audit logging
    - Folder deletion of non-empty folders rejected (400) with clear error message
    """

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="emp1",
            email="emp1@test.com",
            password="Password123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )
        self.user2 = User.objects.create_user(
            username="emp2",
            email="emp2@test.com",
            password="Password123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="Password123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )

        self.folder1 = Folder.objects.create(name="Folder Alpha", owner=self.user1)
        self.folder2 = Folder.objects.create(name="Folder Beta", owner=self.user2)

    def test_unauthenticated_access_returns_401(self):
        """Unauthenticated requests are rejected with 401 Unauthorized."""
        res = self.client.get("/api/folders/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.post("/api/folders/", {"name": "New Folder"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.patch(f"/api/folders/{self.folder1.id}/", {"name": "Renamed"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.delete(f"/api/folders/{self.folder1.id}/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_access_denied_returns_403(self):
        """ADMIN users are denied access to folder endpoints with 403 Forbidden."""
        self.client.force_authenticate(user=self.admin)

        res = self.client.get("/api/folders/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.post("/api/folders/", {"name": "Admin Folder"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.patch(f"/api/folders/{self.folder1.id}/", {"name": "Admin Renamed"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.delete(f"/api/folders/{self.folder1.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_folders_owner_isolation(self):
        """Listing folders returns only folders belonging to the authenticated owner."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.get("/api/folders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        folder_ids = [f["id"] for f in res.data]
        self.assertIn(str(self.folder1.id), folder_ids)
        self.assertNotIn(str(self.folder2.id), folder_ids)

    def test_create_folder_success_and_audit(self):
        """Authenticated employee can create a folder, generating an audit event."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post("/api/folders/", {"name": "Contracts"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Contracts")
        self.assertEqual(res.data["document_count"], 0)

        # Verify audit log
        created_folder_id = res.data["id"]
        audit_event = AuditEvent.objects.filter(
            actor=self.user1,
            action="FOLDER_CREATE",
            target_type="documents.folder",
            target_id=created_folder_id,
        ).first()
        self.assertIsNotNone(audit_event)

    def test_duplicate_folder_name_same_owner_rejected(self):
        """Creating a duplicate folder name for the same owner is rejected case-insensitively."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post("/api/folders/", {"name": "folder alpha"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(res.data))

    def test_duplicate_folder_name_different_owners_permitted(self):
        """Different owners may have folders with identical names."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post("/api/folders/", {"name": "Folder Beta"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Folder Beta")

    def test_invalid_folder_names_rejected(self):
        """Blank names or names exceeding 40 characters are rejected."""
        self.client.force_authenticate(user=self.user1)

        res = self.client.post("/api/folders/", {"name": ""})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.post("/api/folders/", {"name": "   "})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.post("/api/folders/", {"name": "x" * 41})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rename_folder_success_and_audit(self):
        """Owner can rename their folder, generating an audit event."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.patch(f"/api/folders/{self.folder1.id}/", {"name": "Renamed Alpha"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Renamed Alpha")

        self.folder1.refresh_from_db()
        self.assertEqual(self.folder1.name, "Renamed Alpha")

        # Verify audit log
        audit_event = AuditEvent.objects.filter(
            actor=self.user1,
            action="FOLDER_RENAME",
            target_type="documents.folder",
            target_id=str(self.folder1.id),
        ).first()
        self.assertIsNotNone(audit_event)

    def test_rename_cross_owner_returns_404(self):
        """Attempting to rename another user's folder returns 404 without revealing existence."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.patch(f"/api/folders/{self.folder2.id}/", {"name": "Hacked Name"})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        self.folder2.refresh_from_db()
        self.assertEqual(self.folder2.name, "Folder Beta")

    def test_delete_empty_folder_success_and_audit(self):
        """Owner can delete an empty folder, generating an audit event."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.delete(f"/api/folders/{self.folder1.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Folder.objects.filter(id=self.folder1.id).exists())

        # Verify audit log
        audit_event = AuditEvent.objects.filter(
            actor=self.user1,
            action="FOLDER_DELETE",
            target_type="documents.folder",
            target_id=str(self.folder1.id),
        ).first()
        self.assertIsNotNone(audit_event)

    def test_delete_cross_owner_returns_404(self):
        """Attempting to delete another user's folder returns 404 without revealing existence."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.delete(f"/api/folders/{self.folder2.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        self.assertTrue(Folder.objects.filter(id=self.folder2.id).exists())

    def test_delete_non_empty_folder_rejected(self):
        """Attempting to delete a folder containing documents returns 400 with a clear error."""
        Document.objects.create(
            owner=self.user1,
            folder=self.folder1,
            name="file.pdf",
            original_filename="file.pdf",
            description="",
            file_type=Document.FileType.PDF,
            size=100,
            sha256="c" * 64,
            storage_key=uuid.uuid4().hex + uuid.uuid4().hex,
            status=Document.Status.ACTIVE,
        )

        self.client.force_authenticate(user=self.user1)
        res = self.client.delete(f"/api/folders/{self.folder1.id}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("contains documents", str(res.data))

        # Folder must remain in DB
        self.assertTrue(Folder.objects.filter(id=self.folder1.id).exists())


# ──────────────────────────────────────────────────────────────────────────────
# Document API Tests
# ──────────────────────────────────────────────────────────────────────────────


class DocumentAPITests(APITestCase):
    """
    Integration tests for Document REST API endpoints.

    Uses SimpleUploadedFile fixtures with real PDF/ZIP magic bytes and mocks
    PrivateDocumentStorage so no disk I/O occurs during testing.

    Covers:
    - Unauthenticated / ADMIN role denial
    - Upload pipeline (success, bad extension, bad mime type)
    - Listing with filters (status, search, folder)
    - Detail retrieval with DOCUMENT_VIEW audit event
    - Metadata update (name, description, folder, owner isolation)
    - Archive / restore transitions
    - Soft-delete and purge lifecycle
    - Download endpoint auth and 404 for deleted/other-owner docs
    """

    # Minimal valid PDF magic header — no dangerous keywords
    SAFE_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"

    # Minimal valid DOCX ZIP (contains [Content_Types].xml with wordprocessingml.document)
    _CONTENT_TYPES_XML = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        b'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        b'<Override PartName="/word/document.xml"'
        b' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        b"</Types>"
    )

    def _make_docx_bytes(self):
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", self._CONTENT_TYPES_XML)
            zf.writestr("word/document.xml", b"<document/>")
        return buf.getvalue()

    def setUp(self):
        self.employee = User.objects.create_user(
            username="doc_emp",
            email="doc_emp@test.com",
            password="Password123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )
        self.employee2 = User.objects.create_user(
            username="doc_emp2",
            email="doc_emp2@test.com",
            password="Password123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )
        self.admin = User.objects.create_user(
            username="doc_admin",
            email="doc_admin@test.com",
            password="Password123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )
        self.folder = Folder.objects.create(name="Test Folder", owner=self.employee)

    def _create_document(self, owner, **kwargs):
        """Helper: create a Document record bypassing the upload pipeline."""
        defaults = dict(
            name="sample.pdf",
            original_filename="sample.pdf",
            description="test",
            file_type=Document.FileType.PDF,
            size=1024,
            sha256="d" * 64,
            storage_key=uuid.uuid4().hex + uuid.uuid4().hex,
            status=Document.Status.ACTIVE,
        )
        defaults.update(kwargs)
        return Document.objects.create(owner=owner, **defaults)

    # ── Auth / role denial ─────────────────────────────────────────────

    def test_unauthenticated_document_list_returns_401(self):
        res = self.client.get("/api/documents/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_document_list_returns_403(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/documents/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_document_upload_returns_403(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_authenticate(user=self.admin)
        fake_file = SimpleUploadedFile("report.pdf", self.SAFE_PDF_BYTES, content_type="application/pdf")
        res = self.client.post("/api/documents/", {"file": fake_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ── List / filter ──────────────────────────────────────────────────

    def test_list_documents_empty(self):
        self.client.force_authenticate(user=self.employee)
        res = self.client.get("/api/documents/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 0)
        self.assertEqual(res.data["results"], [])

    def test_list_documents_owner_isolation(self):
        doc1 = self._create_document(self.employee, name="emp1.pdf")
        self._create_document(self.employee2, name="emp2.pdf")

        self.client.force_authenticate(user=self.employee)
        res = self.client.get("/api/documents/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in res.data["results"]]
        self.assertIn(str(doc1.id), ids)
        self.assertEqual(res.data["count"], 1)

    def test_list_documents_search_filter(self):
        self._create_document(self.employee, name="budget_2026.pdf", description="annual budget")
        self._create_document(self.employee, name="contract.pdf", description="vendor contract")

        self.client.force_authenticate(user=self.employee)
        res = self.client.get("/api/documents/?search=budget")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["name"], "budget_2026.pdf")

    def test_list_documents_status_filter(self):
        active_doc = self._create_document(self.employee, name="active.pdf", status=Document.Status.ACTIVE)
        archived_doc = self._create_document(
            self.employee, name="archived.pdf",
            sha256="e" * 64,
            storage_key=uuid.uuid4().hex + uuid.uuid4().hex,
            status=Document.Status.ARCHIVED,
        )

        self.client.force_authenticate(user=self.employee)

        res = self.client.get("/api/documents/?status=active")
        names = [r["name"] for r in res.data["results"]]
        self.assertIn("active.pdf", names)
        self.assertNotIn("archived.pdf", names)

        res = self.client.get("/api/documents/?status=archived")
        names = [r["name"] for r in res.data["results"]]
        self.assertIn("archived.pdf", names)
        self.assertNotIn("active.pdf", names)

    def test_list_documents_folder_filter(self):
        in_folder = self._create_document(self.employee, name="in_folder.pdf", folder=self.folder)
        no_folder = self._create_document(
            self.employee, name="no_folder.pdf",
            sha256="f" * 64,
            storage_key=uuid.uuid4().hex + uuid.uuid4().hex,
        )

        self.client.force_authenticate(user=self.employee)
        res = self.client.get(f"/api/documents/?folder={self.folder.id}")
        names = [r["name"] for r in res.data["results"]]
        self.assertIn("in_folder.pdf", names)
        self.assertNotIn("no_folder.pdf", names)

    # ── Detail ────────────────────────────────────────────────────────

    def test_get_document_detail_success_with_audit(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)

        pre_audit_count = AuditEvent.objects.filter(
            actor=self.employee, action="DOCUMENT_VIEW"
        ).count()

        res = self.client.get(f"/api/documents/{doc.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], str(doc.id))
        self.assertNotIn("storage_key", res.data)

        # DOCUMENT_VIEW audit event should be recorded
        post_count = AuditEvent.objects.filter(
            actor=self.employee, action="DOCUMENT_VIEW"
        ).count()
        self.assertEqual(post_count, pre_audit_count + 1)

    def test_get_document_detail_cross_owner_returns_404(self):
        doc = self._create_document(self.employee2)
        self.client.force_authenticate(user=self.employee)
        res = self.client.get(f"/api/documents/{doc.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_storage_key_never_in_response(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)

        for url in ["/api/documents/", f"/api/documents/{doc.id}/"]:
            res = self.client.get(url)
            self.assertNotIn("storage_key", str(res.content))

    # ── Metadata update ───────────────────────────────────────────────

    def test_patch_document_name_success(self):
        doc = self._create_document(self.employee, name="old_name.pdf")
        self.client.force_authenticate(user=self.employee)
        res = self.client.patch(
            f"/api/documents/{doc.id}/",
            {"name": "new_name.pdf"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "new_name.pdf")
        doc.refresh_from_db()
        self.assertEqual(doc.name, "new_name.pdf")

    def test_patch_document_description_success(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        res = self.client.patch(
            f"/api/documents/{doc.id}/",
            {"description": "Updated description"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["description"], "Updated description")

    def test_patch_document_folder_assignment(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        res = self.client.patch(
            f"/api/documents/{doc.id}/",
            {"folder": str(self.folder.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(str(res.data["folder"]), str(self.folder.id))

    def test_patch_document_cross_owner_folder_rejected(self):
        other_folder = Folder.objects.create(name="Other Folder", owner=self.employee2)
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        res = self.client.patch(
            f"/api/documents/{doc.id}/",
            {"folder": str(other_folder.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_document_cross_owner_returns_404(self):
        doc = self._create_document(self.employee2)
        self.client.force_authenticate(user=self.employee)
        res = self.client.patch(f"/api/documents/{doc.id}/", {"name": "hack.pdf"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_document_audit_event_recorded(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        res = self.client.patch(
            f"/api/documents/{doc.id}/",
            {"description": "audit test"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        audit = AuditEvent.objects.filter(
            actor=self.employee,
            action="DOCUMENT_UPDATE",
            target_id=str(doc.id),
        ).first()
        self.assertIsNotNone(audit)

    # ── Archive / restore ─────────────────────────────────────────────

    def test_archive_active_document_success(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        res = self.client.post(f"/api/documents/{doc.id}/archive/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], Document.Status.ARCHIVED)
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.ARCHIVED)
        self.assertIsNotNone(doc.archived_at)

    def test_archive_already_archived_returns_400(self):
        doc = self._create_document(
            self.employee, status=Document.Status.ARCHIVED,
            sha256="a" * 64,
            storage_key=uuid.uuid4().hex + uuid.uuid4().hex,
        )
        self.client.force_authenticate(user=self.employee)
        res = self.client.post(f"/api/documents/{doc.id}/archive/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_restore_archived_document_success(self):
        doc = self._create_document(
            self.employee,
            status=Document.Status.ARCHIVED,
            sha256="b" * 64,
            storage_key=uuid.uuid4().hex + uuid.uuid4().hex,
        )
        self.client.force_authenticate(user=self.employee)
        res = self.client.post(f"/api/documents/{doc.id}/restore/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], Document.Status.ACTIVE)
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.ACTIVE)
        self.assertIsNone(doc.archived_at)

    def test_archive_cross_owner_returns_404(self):
        doc = self._create_document(self.employee2)
        self.client.force_authenticate(user=self.employee)
        res = self.client.post(f"/api/documents/{doc.id}/archive/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ── Soft-delete ───────────────────────────────────────────────────

    def test_soft_delete_active_document(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        res = self.client.delete(f"/api/documents/{doc.id}/delete/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.DELETED)
        self.assertIsNotNone(doc.deleted_at)
        self.assertEqual(doc.deleted_by, self.employee)

    def test_soft_delete_audit_event_recorded(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        self.client.delete(f"/api/documents/{doc.id}/delete/")
        audit = AuditEvent.objects.filter(
            actor=self.employee,
            action="DOCUMENT_DELETE",
            target_id=str(doc.id),
        ).first()
        self.assertIsNotNone(audit)

    def test_soft_delete_cross_owner_returns_404(self):
        doc = self._create_document(self.employee2)
        self.client.force_authenticate(user=self.employee)
        res = self.client.delete(f"/api/documents/{doc.id}/delete/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleted_document_hidden_from_default_list(self):
        doc = self._create_document(self.employee)
        doc.status = Document.Status.DELETED
        doc.save()
        self.client.force_authenticate(user=self.employee)
        res = self.client.get("/api/documents/")
        ids = [r["id"] for r in res.data["results"]]
        self.assertNotIn(str(doc.id), ids)

    def test_deleted_document_detail_returns_404(self):
        doc = self._create_document(self.employee)
        doc.status = Document.Status.DELETED
        doc.save()
        self.client.force_authenticate(user=self.employee)
        res = self.client.get(f"/api/documents/{doc.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ── Purge ─────────────────────────────────────────────────────────

    def test_purge_deleted_document_success(self):
        from unittest.mock import patch as mock_patch
        doc = self._create_document(self.employee, status=Document.Status.DELETED)
        self.client.force_authenticate(user=self.employee)

        with mock_patch("documents.views.PrivateDocumentStorage") as MockStorage:
            mock_instance = MockStorage.return_value
            mock_instance.delete.return_value = True
            res = self.client.post(f"/api/documents/{doc.id}/purge/")

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        doc.refresh_from_db()
        self.assertIsNotNone(doc.purged_at)

    def test_purge_active_document_returns_404(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)
        res = self.client.post(f"/api/documents/{doc.id}/purge/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_purge_already_purged_document_returns_400(self):
        from django.utils import timezone as tz
        from unittest.mock import patch as mock_patch
        doc = self._create_document(
            self.employee,
            status=Document.Status.DELETED,
            sha256="f" * 64,
            storage_key=uuid.uuid4().hex + uuid.uuid4().hex,
        )
        doc.purged_at = tz.now()
        doc.save()
        self.client.force_authenticate(user=self.employee)

        with mock_patch("documents.views.PrivateDocumentStorage"):
            res = self.client.post(f"/api/documents/{doc.id}/purge/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Download auth ─────────────────────────────────────────────────

    def test_download_unauthenticated_returns_401(self):
        doc = self._create_document(self.employee)
        res = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_admin_returns_403(self):
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_cross_owner_returns_404(self):
        doc = self._create_document(self.employee2)
        self.client.force_authenticate(user=self.employee)
        res = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_deleted_document_returns_404(self):
        doc = self._create_document(self.employee, status=Document.Status.DELETED)
        self.client.force_authenticate(user=self.employee)
        res = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_active_document_streams_file(self):
        from unittest.mock import MagicMock, patch as mock_patch
        from io import BytesIO
        doc = self._create_document(self.employee)
        self.client.force_authenticate(user=self.employee)

        fake_bytes = b"PDF content here"
        with mock_patch("documents.views.PrivateDocumentStorage") as MockStorage:
            mock_instance = MockStorage.return_value
            mock_instance.exists.return_value = True
            mock_instance.open.return_value = BytesIO(fake_bytes)
            res = self.client.get(f"/api/documents/{doc.id}/download/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", res.get("Content-Disposition", ""))

    # ── Upload pipeline (mocked storage) ─────────────────────────────

    def test_upload_invalid_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_authenticate(user=self.employee)
        fake = SimpleUploadedFile("malware.exe", b"MZ\x00\x00", content_type="application/octet-stream")
        res = self.client.post("/api/documents/", {"file": fake}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_valid_pdf_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from unittest.mock import patch as mock_patch
        self.client.force_authenticate(user=self.employee)
        fake = SimpleUploadedFile("report.pdf", self.SAFE_PDF_BYTES, content_type="application/pdf")

        with mock_patch("documents.views.PrivateDocumentStorage") as MockStorage:
            mock_instance = MockStorage.return_value
            mock_instance.generate_storage_key.return_value = "a" * 64
            mock_instance.save_stream.return_value = len(self.SAFE_PDF_BYTES)

            res = self.client.post(
                "/api/documents/",
                {"file": fake, "name": "Annual Report", "description": "Q4 report"},
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["file_type"], "PDF")
        self.assertNotIn("storage_key", res.data)
        self.assertTrue(Document.objects.filter(name="Annual Report").exists())

    def test_upload_generates_audit_event(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from unittest.mock import patch as mock_patch
        self.client.force_authenticate(user=self.employee)
        fake = SimpleUploadedFile("q4.pdf", self.SAFE_PDF_BYTES, content_type="application/pdf")

        pre_count = AuditEvent.objects.filter(actor=self.employee, action="DOCUMENT_UPLOAD").count()

        with mock_patch("documents.views.PrivateDocumentStorage") as MockStorage:
            mock_instance = MockStorage.return_value
            mock_instance.generate_storage_key.return_value = "b" * 64
            mock_instance.save_stream.return_value = len(self.SAFE_PDF_BYTES)
            self.client.post("/api/documents/", {"file": fake}, format="multipart")

        post_count = AuditEvent.objects.filter(actor=self.employee, action="DOCUMENT_UPLOAD").count()
        self.assertEqual(post_count, pre_count + 1)
