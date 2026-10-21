import uuid
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.test import RequestFactory, TestCase

from auditlog.admin import AuditEventAdmin
from auditlog.helpers import AuditLogFailureError, log_event
from auditlog.models import AuditEvent

User = get_user_model()


class MockTarget:
    """Mock model instance to verify target PK handling (supports UUID and ints)."""

    def __init__(self, pk, app_label="documents", model_name="Document"):
        self.pk = pk
        self._meta = mock.Mock()
        self._meta.app_label = app_label
        self._meta.model_name = model_name


class AuditEventModelTests(TestCase):
    """Tests for AuditEvent model creation, UUID support, and immutability guards."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="audit_test_user",
            email="audit_user@example.com",
            password="testpassword123",
            role=User.Role.EMPLOYEE,
        )

    def test_create_audit_event_with_uuid_target_id(self):
        """AuditEvent must accept and correctly store a standard UUID string for target_id."""
        doc_uuid = uuid.uuid4()
        event = AuditEvent.objects.create(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target_type="documents.Document",
            target_id=str(doc_uuid),
            metadata={"file_size": 1024, "content_type": "application/pdf"},
        )
        self.assertIsNotNone(event.pk)
        self.assertEqual(event.target_id, str(doc_uuid))

        # Query back by composite index target_type + target_id
        fetched = AuditEvent.objects.get(target_type="documents.Document", target_id=str(doc_uuid))
        self.assertEqual(fetched.pk, event.pk)

    def test_create_audit_event_with_integer_target_id(self):
        """AuditEvent must accept and correctly store an integer ID as string for target_id."""
        event = AuditEvent.objects.create(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_VIEW,
            target_type="accounts.User",
            target_id=str(self.user.pk),
        )
        self.assertEqual(event.target_id, str(self.user.pk))

    def test_direct_model_creation_sanitizes_metadata_at_save(self):
        """Direct creation of AuditEvent via ORM must sanitize metadata via allowlist on save()."""
        event = AuditEvent.objects.create(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target_type="documents.Document",
            target_id="doc-direct-789",
            metadata={
                "filename": "Direct_Secret.pdf",
                "secret_key": "api_secret_key_123",
                "file_size": 4096,
                "content_type": "application/pdf",
            },
        )
        self.assertNotIn("filename", event.metadata)
        self.assertNotIn("secret_key", event.metadata)
        self.assertEqual(event.metadata["file_size"], 4096)
        self.assertEqual(event.metadata["content_type"], "application/pdf")

    def test_immutability_save_existing_record_raises_permission_error(self):
        """Updating an existing AuditEvent via save() must raise PermissionError."""
        event = AuditEvent.objects.create(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target_type="documents.Document",
            target_id="doc-123",
        )
        event.action = AuditEvent.Action.DOCUMENT_DELETE
        with self.assertRaises(PermissionError) as ctx:
            event.save()
        self.assertIn("immutable", str(ctx.exception).lower())

    def test_immutability_delete_record_raises_permission_error(self):
        """Deleting an AuditEvent via delete() must raise PermissionError."""
        event = AuditEvent.objects.create(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target_type="documents.Document",
            target_id="doc-456",
        )
        with self.assertRaises(PermissionError) as ctx:
            event.delete()
        self.assertIn("immutable", str(ctx.exception).lower())


class AuditLogHelperTests(TestCase):
    """Tests for log_event helper, failure handling, and fail-closed rollback behavior."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="helper_test_user",
            email="helper_user@example.com",
            password="testpassword123",
            role=User.Role.EMPLOYEE,
        )

    def test_log_event_success_returns_event(self):
        """log_event creates and returns the AuditEvent instance."""
        target = MockTarget(pk=uuid.uuid4())
        event = log_event(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target=target,
            metadata={"file_size": 5000},
        )
        self.assertIsNotNone(event)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.target_id, str(target.pk))
        self.assertEqual(event.target_type, "documents.Document")

    def test_point_of_recording_metadata_sanitization_strips_disallowed_keys(self):
        """
        log_event must enforce point-of-recording allowlist filtering.
        Raw filenames, file contents, secrets, passwords, tokens, and arbitrary
        nested structures must be stripped before persistence.
        """
        raw_metadata = {
            "filename": "Payroll_Q4_Confidential.pdf",
            "original_filename": "secret_tax_records.pdf",
            "title": "Private Memo",
            "content": "Secret salary data text...",
            "file_size": 1048576,
            "content_type": "application/pdf",
            "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "file_extension": ".pdf",
            "secret_token": "sk_live_123456789",
            "password": "supersecretpassword",
            "nested_payload": {"sensitive": "leak"},
        }
        event = log_event(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target=MockTarget(pk=uuid.uuid4()),
            metadata=raw_metadata,
        )
        # Disallowed fields must be completely stripped
        self.assertNotIn("filename", event.metadata)
        self.assertNotIn("original_filename", event.metadata)
        self.assertNotIn("title", event.metadata)
        self.assertNotIn("content", event.metadata)
        self.assertNotIn("secret_token", event.metadata)
        self.assertNotIn("password", event.metadata)
        self.assertNotIn("nested_payload", event.metadata)

        # Permitted allowlist fields must be accurately preserved
        self.assertEqual(event.metadata["file_size"], 1048576)
        self.assertEqual(event.metadata["content_type"], "application/pdf")
        self.assertEqual(event.metadata["sha256_hash"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(event.metadata["sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(event.metadata["file_extension"], ".pdf")

    def test_point_of_recording_metadata_handles_non_dict_and_none(self):
        """Non-dict metadata inputs (e.g. str, list, None) must be safely sanitized to {}."""
        event1 = log_event(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_VIEW,
            target=MockTarget(pk=1),
            metadata="malformed_string_metadata",
        )
        self.assertEqual(event1.metadata, {})

        event2 = log_event(
            actor=self.user,
            action=AuditEvent.Action.DOCUMENT_VIEW,
            target=MockTarget(pk=2),
            metadata=None,
        )
        self.assertEqual(event2.metadata, {})

    def test_fail_open_mode_on_write_failure(self):
        """When fail_closed=False (default), write failure logs error and returns None without raising."""
        with mock.patch("auditlog.helpers.AuditEvent.objects.create", side_effect=DatabaseError("DB write failure")):
            result = log_event(
                actor=self.user,
                action=AuditEvent.Action.DOCUMENT_VIEW,
                target=MockTarget(pk=1),
                fail_closed=False,
            )
            self.assertIsNone(result)

    def test_fail_closed_mode_on_write_failure_raises_audit_log_failure_error(self):
        """When fail_closed=True, write failure raises AuditLogFailureError."""
        with mock.patch("auditlog.helpers.AuditEvent.objects.create", side_effect=DatabaseError("Disk full")):
            with self.assertRaises(AuditLogFailureError) as ctx:
                log_event(
                    actor=self.user,
                    action=AuditEvent.Action.DOCUMENT_DELETE,
                    target=MockTarget(pk=1),
                    fail_closed=True,
                )
            self.assertIn("Security audit logging failed", str(ctx.exception))

    def test_fail_closed_aborts_and_rolls_back_outer_transaction(self):
        """
        When a critical operation requires audit logging (fail_closed=True) and
        audit logging fails, the caller's entire database transaction must roll back.
        """
        initial_user_count = User.objects.count()

        try:
            with transaction.atomic():
                # Perform business operation that must not persist without an audit record
                User.objects.create_user(
                    username="user_should_be_rolled_back",
                    email="rollback@example.com",
                    password="password123",
                )
                # Attempt critical audit log that fails
                with mock.patch("auditlog.helpers.AuditEvent.objects.create", side_effect=DatabaseError("DB Error")):
                    log_event(
                        actor=self.user,
                        action=AuditEvent.Action.DOCUMENT_DELETE,
                        target=MockTarget(pk=99),
                        fail_closed=True,
                    )
        except AuditLogFailureError:
            pass  # Expected exception caught

        # Verify database operation was rolled back
        self.assertFalse(User.objects.filter(username="user_should_be_rolled_back").exists())
        self.assertEqual(User.objects.count(), initial_user_count)

    def test_fail_open_preserves_outer_transaction_on_failure(self):
        """
        When non-critical audit logging runs (fail_closed=False) inside a transaction,
        a failed audit write does NOT abort or corrupt the outer transaction.
        """
        with transaction.atomic():
            created_user = User.objects.create_user(
                username="user_should_persist",
                email="persist@example.com",
                password="password123",
            )
            # Fail-open audit logging fails
            with mock.patch("auditlog.helpers.AuditEvent.objects.create", side_effect=DatabaseError("DB Error")):
                result = log_event(
                    actor=self.user,
                    action=AuditEvent.Action.DOCUMENT_VIEW,
                    target=MockTarget(pk=created_user.pk),
                    fail_closed=False,
                )
            self.assertIsNone(result)

        # Verify business operation persisted despite non-critical audit log failure
        self.assertTrue(User.objects.filter(username="user_should_persist").exists())


class AuditEventAdminAccessAndPrivacyTests(TestCase):
    """Tests for AuditEventAdmin access control and metadata privacy sanitization."""

    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = AuditEventAdmin(AuditEvent, self.site)

        # Active Administrator
        self.admin_user = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="adminpassword123",
            role=User.Role.ADMIN,
            is_staff=True,
            status=User.Status.ACTIVE,
        )

        # Active Employee (regular staff=False)
        self.employee_user = User.objects.create_user(
            username="employee_user",
            email="employee@example.com",
            password="employeepassword123",
            role=User.Role.EMPLOYEE,
            is_staff=False,
            status=User.Status.ACTIVE,
        )

        # Employee mistakenly given is_staff=True (privilege escalation attempt)
        self.staff_employee = User.objects.create_user(
            username="staff_employee",
            email="staff_emp@example.com",
            password="employeepassword123",
            role=User.Role.EMPLOYEE,
            is_staff=True,
            status=User.Status.ACTIVE,
        )

        # Suspended Admin
        self.suspended_admin = User.objects.create_user(
            username="suspended_admin",
            email="suspended_admin@example.com",
            password="adminpassword123",
            role=User.Role.ADMIN,
            is_staff=True,
            status=User.Status.SUSPENDED,
            is_active=False,
        )

    def _build_request(self, user):
        request = self.factory.get("/admin/auditlog/auditevent/")
        request.user = user
        return request

    def test_active_admin_has_module_and_view_permission(self):
        """Active staff user with ADMIN role can access the audit log module and view records."""
        req = self._build_request(self.admin_user)
        self.assertTrue(self.admin.has_module_permission(req))
        self.assertTrue(self.admin.has_view_permission(req))

    def test_regular_employee_denied_admin_access(self):
        """Regular employee is denied module and view permissions."""
        req = self._build_request(self.employee_user)
        self.assertFalse(self.admin.has_module_permission(req))
        self.assertFalse(self.admin.has_view_permission(req))

    def test_employee_with_is_staff_denied_admin_access(self):
        """Employee user even with is_staff=True is denied access because role != ADMIN."""
        req = self._build_request(self.staff_employee)
        self.assertFalse(self.admin.has_module_permission(req))
        self.assertFalse(self.admin.has_view_permission(req))

    def test_suspended_admin_denied_admin_access(self):
        """Suspended admin user is denied access."""
        req = self._build_request(self.suspended_admin)
        self.assertFalse(self.admin.has_module_permission(req))
        self.assertFalse(self.admin.has_view_permission(req))

    def test_admin_modifications_strictly_forbidden(self):
        """AuditEventAdmin must forbid add, change, and delete operations for all users."""
        req = self._build_request(self.admin_user)
        self.assertFalse(self.admin.has_add_permission(req))
        self.assertFalse(self.admin.has_change_permission(req))
        self.assertFalse(self.admin.has_delete_permission(req))

    def test_safe_metadata_display_redacts_sensitive_filenames_and_contents(self):
        """
        Metadata display in Django admin must strictly redact sensitive document filenames,
        titles, and contents, while preserving operational fields like file_size and hash.
        """
        event = AuditEvent(
            actor=self.admin_user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target_type="documents.Document",
            target_id="doc-999",
            metadata={
                "filename": "Confidential_Q3_Financials.pdf",
                "original_filename": "top_secret_merger.pdf",
                "title": "Board Executive Summary",
                "content": "Secret internal memo text",
                "file_size": 204800,
                "content_type": "application/pdf",
                "sha256": "abcdef1234567890",
            },
        )
        rendered_html = str(self.admin.safe_metadata(event))

        # Sensitive values must NOT appear anywhere in the rendered HTML
        self.assertNotIn("Confidential_Q3_Financials.pdf", rendered_html)
        self.assertNotIn("top_secret_merger.pdf", rendered_html)
        self.assertNotIn("Board Executive Summary", rendered_html)
        self.assertNotIn("Secret internal memo text", rendered_html)

        # Redaction marker must be present
        self.assertIn("[REDACTED_FOR_SECURITY]", rendered_html)

        # Safe operational metadata must remain visible
        self.assertIn("204800", rendered_html)
        self.assertIn("application/pdf", rendered_html)
        self.assertIn("abcdef1234567890", rendered_html)

    def test_admin_list_display_and_search_exclude_content_fields(self):
        """Verify list_display, search_fields, and list_filter do not reference filenames or content."""
        forbidden_fields = {"filename", "original_filename", "content", "title", "file"}

        for field in self.admin.list_display:
            self.assertNotIn(field.lower(), forbidden_fields)

        for field in self.admin.search_fields:
            self.assertNotIn(field.lower(), forbidden_fields)

        for field in self.admin.list_filter:
            self.assertNotIn(field.lower(), forbidden_fields)
