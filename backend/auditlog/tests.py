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


from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.authentication import create_tab_session


class TabSessionTestMixin:
    def authenticate_as(self, user):
        user.backend = "accounts.backends.EmailOrUsernameBackend"
        self.client.credentials(
            HTTP_X_DOCTRUST_SESSION=create_tab_session(user, remember_me=True),
        )


class AuditAPITests(TabSessionTestMixin, APITestCase):
    """Tests for the Permission Audits REST API views."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_auditor",
            email="admin_auditor@example.com",
            password="admin_password123",
            role=User.Role.ADMIN,
        )
        self.employee_user = User.objects.create_user(
            username="employee_subject",
            email="employee_subject@example.com",
            password="emp_password123",
            role=User.Role.EMPLOYEE,
        )
        self.other_employee = User.objects.create_user(
            username="other_emp",
            email="other_emp@example.com",
            password="other_password123",
            role=User.Role.EMPLOYEE,
        )

        # Create sample events
        self.admin_event = AuditEvent.objects.create(
            actor=self.admin_user,
            action=AuditEvent.Action.LOGIN_SUCCESS,
            target_type="accounts.User",
            target_id=str(self.admin_user.pk),
            ip_address="127.0.0.1",
        )
        self.admin_fail_event = AuditEvent.objects.create(
            actor=self.admin_user,
            action=AuditEvent.Action.LOGIN_FAILED,
            target_type="accounts.User",
            target_id=str(self.admin_user.pk),
            ip_address="127.0.0.1",
            metadata={"reason": "invalid_credentials"},
        )
        self.emp_event = AuditEvent.objects.create(
            actor=self.employee_user,
            action=AuditEvent.Action.DOCUMENT_UPLOAD,
            target_type="documents.Document",
            target_id="doc-101",
            ip_address="192.168.1.50",
            metadata={"file_size": 2048, "content_type": "application/pdf"},
        )
        self.emp_doc_delete = AuditEvent.objects.create(
            actor=self.other_employee,
            action=AuditEvent.Action.DOCUMENT_DELETE,
            target_type="documents.Document",
            target_id="doc-202",
            ip_address="192.168.1.51",
        )

    def test_unauthenticated_access_rejected(self):
        """Unauthenticated requests to audit endpoints must be denied."""
        endpoints = [
            "/api/audit/admin/",
            "/api/audit/employee/",
            f"/api/audit/events/{self.admin_event.pk}/",
            "/api/audit/admin/export/",
            "/api/audit/employee/export/",
            "/api/audit/action-types/",
            "/api/audit/users/",
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertIn(
                response.status_code,
                [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                f"Expected 401/403 for unauthenticated GET {url}, got {response.status_code}",
            )

    def test_employee_access_forbidden(self):
        """Employee users must receive 403 Forbidden on all audit endpoints."""
        self.authenticate_as(self.employee_user)
        endpoints = [
            "/api/audit/admin/",
            "/api/audit/employee/",
            f"/api/audit/events/{self.admin_event.pk}/",
            "/api/audit/admin/export/",
            "/api/audit/employee/export/",
            "/api/audit/action-types/",
            "/api/audit/users/",
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Expected 403 for employee GET {url}, got {response.status_code}",
            )

    def test_admin_list_admin_events(self):
        """Admin list endpoint returns only events performed by ADMIN actors."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/admin/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 2)
        results = response.data["results"]
        for item in results:
            self.assertEqual(item["actor_role"], "ADMIN")

    def test_admin_list_employee_events(self):
        """Employee list endpoint returns only events performed by EMPLOYEE actors."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/employee/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 2)
        results = response.data["results"]
        for item in results:
            self.assertEqual(item["actor_role"], "EMPLOYEE")

    def test_filter_by_search(self):
        """Search query filters across actor username, action, and target fields."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/employee/?search=doc-101")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(response.data["results"][0]["target_id"], "doc-101")

        response = self.client.get("/api/audit/employee/?search=other_emp")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)

    def test_filter_by_action_type(self):
        """Filter by action_type returns only matching events."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/employee/?action_type=DOCUMENT_UPLOAD")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(response.data["results"][0]["action"], "DOCUMENT_UPLOAD")

    def test_filter_by_user(self):
        """Filter by user username returns only events for that user."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/employee/?user=other_emp")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(response.data["results"][0]["actor_username"], "other_emp")

    def test_filter_by_outcome(self):
        """Filter by outcome (success vs failed) correctly partitions events."""
        self.authenticate_as(self.admin_user)
        res_fail = self.client.get("/api/audit/admin/?outcome=failed")
        self.assertEqual(res_fail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_fail.data["total_count"], 1)
        self.assertEqual(res_fail.data["results"][0]["outcome"], "Failed")

        res_succ = self.client.get("/api/audit/admin/?outcome=success")
        self.assertEqual(res_succ.status_code, status.HTTP_200_OK)
        self.assertEqual(res_succ.data["total_count"], 1)
        self.assertEqual(res_succ.data["results"][0]["outcome"], "Success")

    def test_pagination(self):
        """Pagination returns correct page, page_size, and total_pages."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/employee/?page=1&page_size=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["total_count"], 2)
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["page_size"], 1)
        self.assertEqual(response.data["total_pages"], 2)

    def test_event_detail_endpoint(self):
        """Event detail endpoint returns full event details with safe metadata."""
        self.authenticate_as(self.admin_user)
        response = self.client.get(f"/api/audit/events/{self.emp_event.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.emp_event.pk)
        self.assertEqual(response.data["actor_username"], "employee_subject")
        self.assertEqual(response.data["actor_role"], "EMPLOYEE")
        self.assertEqual(response.data["action"], "DOCUMENT_UPLOAD")
        self.assertEqual(response.data["target_id"], "doc-101")
        self.assertEqual(response.data["safe_metadata"]["file_size"], 2048)

    def test_event_detail_404_for_nonexistent(self):
        """Event detail returns 404 for non-existent event ID."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/events/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_admin(self):
        """Admin CSV export returns text/csv with correct headers and rows."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/admin/export/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("Timestamp,User,Role,Action,Description,Target Resource,IP Address,Outcome", content)
        self.assertIn("admin_auditor", content)

    def test_csv_export_employee(self):
        """Employee CSV export returns text/csv with correct employee records."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/employee/export/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode("utf-8")
        self.assertIn("employee_subject", content)
        self.assertNotIn("admin_auditor", content)

    def test_action_types_endpoint(self):
        """Action types endpoint returns all defined AuditEvent actions."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/action-types/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        values = [item["value"] for item in response.data["action_types"]]
        self.assertIn("DOCUMENT_UPLOAD", values)
        self.assertIn("LOGIN_SUCCESS", values)
        self.assertIn("LOGIN_FAILED", values)

    def test_audit_users_endpoint(self):
        """Audit users endpoint returns usernames of actors who have audit events."""
        self.authenticate_as(self.admin_user)
        response = self.client.get("/api/audit/users/?role=EMPLOYEE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = response.data["users"]
        self.assertIn("employee_subject", usernames)
        self.assertIn("other_emp", usernames)
        self.assertNotIn("admin_auditor", usernames)


class AdminSecurityMonitoringAndDashboardTests(TabSessionTestMixin, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin_sec",
            email="admin_sec@doctrust.local",
            password="AdminPassword123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )
        self.employee = User.objects.create_user(
            username="emp_sec",
            email="emp_sec@doctrust.local",
            password="EmployeePassword123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )
        from auditlog.models import SecurityAlert
        self.alert = SecurityAlert.objects.create(
            title="Multiple failed login attempts detected",
            severity=SecurityAlert.Severity.HIGH,
            status=SecurityAlert.Status.OPEN,
            scope=SecurityAlert.Scope.EMPLOYEE,
            alert_type="FAILED_LOGIN",
            details="5 failed attempts detected",
            target_user=self.employee,
            ip_address="192.168.1.100",
        )

    def test_security_alert_list_and_resolve(self):
        self.authenticate_as(self.admin)
        # List alerts
        resp = self.client.get("/api/audit/security-alerts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("results", resp.data)
        alerts_list = resp.data["results"]
        self.assertTrue(len(alerts_list) >= 1)
        alert_obj = next((a for a in alerts_list if a["id"] == self.alert.id), None)
        self.assertIsNotNone(alert_obj)
        self.assertEqual(alert_obj["status"].upper(), "OPEN")

        # Resolve alert
        resolve_resp = self.client.post(
            f"/api/audit/security-alerts/{self.alert.id}/resolve/",
            {"resolution_notes": "Verified legitimate user password reset."},
            format="json",
        )
        self.assertEqual(resolve_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resolve_resp.data["alert"]["status"].upper(), "RESOLVED")

        # Verify DB persistence
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status.upper(), "RESOLVED")
        self.assertEqual(self.alert.resolved_by, self.admin)
        self.assertIsNotNone(self.alert.resolved_at)

        # Verify audit trail recorded resolution
        audit_res = AuditEvent.objects.filter(action=AuditEvent.Action.SECURITY_ALERT_RESOLVED)
        self.assertTrue(audit_res.exists())

    def test_security_alert_employee_access_forbidden(self):
        self.authenticate_as(self.employee)
        resp = self.client.get("/api/audit/security-alerts/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_stats_endpoint(self):
        self.authenticate_as(self.admin)
        # Test default and range=today
        resp = self.client.get("/api/audit/dashboard-stats/?range=today")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("stats", resp.data)
        self.assertIn("chart_data", resp.data)
        self.assertIn("registered_users", resp.data["stats"])
        self.assertIn("activities", resp.data)

    def test_activity_summary_endpoint(self):
        self.authenticate_as(self.admin)
        resp = self.client.get("/api/audit/activity-summary/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("total_events", resp.data)
        self.assertIn("success_rate", resp.data)
        self.assertIn("active_users_count", resp.data)

    def test_document_overview_zero_trust_access(self):
        self.authenticate_as(self.admin)
        resp = self.client.get("/api/audit/documents-overview/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("total_count", resp.data)
        self.assertIn("results", resp.data)
        for doc in resp.data["results"]:
            self.assertFalse(doc["can_download"])
