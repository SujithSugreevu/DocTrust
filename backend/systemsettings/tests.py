import json
import secrets
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from auditlog.models import AuditEvent
from systemsettings.models import SystemSettings
from systemsettings.services import invalidate_settings_cache

UserModel = get_user_model()


class SystemSettingsModelTestCase(TestCase):
    """Unit tests for the SystemSettings singleton model."""

    def setUp(self):
        invalidate_settings_cache()
        SystemSettings.objects.all().delete()

    def tearDown(self):
        invalidate_settings_cache()

    def test_singleton_load_creates_default(self):
        settings = SystemSettings.load()
        self.assertEqual(settings.pk, 1)
        self.assertEqual(settings.app_name, "DocTrust")
        self.assertIn(".pdf", settings.allowed_file_types)
        self.assertEqual(settings.max_upload_size_mb, 50)
        self.assertFalse(settings.maintenance_mode)
        self.assertFalse(settings.legal_hold_enabled)

    def test_save_always_enforces_id_one(self):
        settings = SystemSettings(pk=99, app_name="CustomTrust")
        settings.save()
        self.assertEqual(settings.pk, 1)
        reloaded = SystemSettings.objects.get(pk=1)
        self.assertEqual(reloaded.app_name, "CustomTrust")

    def test_instance_delete_is_prevented(self):
        settings = SystemSettings.load()
        with self.assertRaises(PermissionError):
            settings.delete()


class SystemSettingsAPITestCase(TestCase):
    """Integration tests for SystemSettings API endpoints."""

    def setUp(self):
        invalidate_settings_cache()
        SystemSettings.objects.all().delete()
        self.client = APIClient()

        # Admin user
        self.admin_user = UserModel.objects.create_user(
            username="admin_test",
            email="admin@doctrust.local",
            password="SecureAdminPassword123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )

        # Employee user
        self.employee_user = UserModel.objects.create_user(
            username="employee_test",
            email="employee@doctrust.local",
            password="SecureEmployeePassword123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )

        self.url = reverse("system-settings")
        self.reset_url = reverse("system-settings-reset")

    def tearDown(self):
        invalidate_settings_cache()

    def test_anonymous_access_denied(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_employee_access_denied(self):
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_retrieve_settings(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["app_name"], "DocTrust")
        self.assertIn("system_health", data)
        self.assertIn("capabilities", data)
        self.assertIn("database", data["system_health"])
        self.assertIn("storage", data["system_health"])

    def test_admin_patch_updates_setting_and_logs_audit(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"app_name": "DocTrust Enterprise", "session_idle_timeout_minutes": 45}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["app_name"], "DocTrust Enterprise")
        self.assertEqual(response.json()["session_idle_timeout_minutes"], 45)

        # Verify audit event was logged
        audit = AuditEvent.objects.filter(action=AuditEvent.Action.SYSTEM_SETTINGS_UPDATE).order_by("-id").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin_user)
        self.assertIn("app_name", audit.metadata.get("changed_fields", ""))

    def test_patch_rejects_invalid_values(self):
        self.client.force_authenticate(user=self.admin_user)
        # session_idle_timeout_minutes must be >= 5
        payload = {"session_idle_timeout_minutes": 2}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("session_idle_timeout_minutes", response.json())

    def test_patch_rejects_unknown_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"unknown_secret_hack": "malicious"}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_maintenance_mode_toggle_logs_special_audit(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"maintenance_mode": True}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        audit = AuditEvent.objects.filter(action=AuditEvent.Action.MAINTENANCE_MODE_TOGGLE).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata.get("maintenance_mode"), "true")

    def test_reset_restores_defaults_and_audits(self):
        self.client.force_authenticate(user=self.admin_user)
        # First modify a setting
        self.client.patch(self.url, data=json.dumps({"app_name": "Modified"}), content_type="application/json")
        # Now reset
        response = self.client.post(self.reset_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["app_name"], "DocTrust")

        audit = AuditEvent.objects.filter(action=AuditEvent.Action.SYSTEM_SETTINGS_RESET).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin_user)


class MaintenanceModeMiddlewareTestCase(TestCase):
    """Test MaintenanceModeMiddleware behavior."""

    def setUp(self):
        invalidate_settings_cache()
        SystemSettings.objects.all().delete()
        self.client = APIClient()

        self.admin_user = UserModel.objects.create_user(
            username="admin_maint",
            email="admin_maint@doctrust.local",
            password="SecureAdminPassword123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )
        self.employee_user = UserModel.objects.create_user(
            username="emp_maint",
            email="emp_maint@doctrust.local",
            password="SecureEmpPassword123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )

    def tearDown(self):
        invalidate_settings_cache()

    def test_non_admin_blocked_with_503_during_maintenance(self):
        settings = SystemSettings.load()
        settings.maintenance_mode = True
        settings.save()
        invalidate_settings_cache()

        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get("/api/documents/")
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json().get("maintenance"))

    def test_admin_bypasses_maintenance(self):
        settings = SystemSettings.load()
        settings.maintenance_mode = True
        settings.save()
        invalidate_settings_cache()

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse("system-settings"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_exempt_paths_accessible_during_maintenance(self):
        settings = SystemSettings.load()
        settings.maintenance_mode = True
        settings.save()
        invalidate_settings_cache()

        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LegalHoldEnforcementTestCase(TestCase):
    """Test legal hold blocks purge operations."""

    def setUp(self):
        invalidate_settings_cache()
        SystemSettings.objects.all().delete()
        self.client = APIClient()

        self.employee = UserModel.objects.create_user(
            username="emp_legal",
            email="emp_legal@doctrust.local",
            password="SecureEmpPassword123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )

    def tearDown(self):
        invalidate_settings_cache()

    def test_legal_hold_blocks_document_purge(self):
        settings = SystemSettings.load()
        settings.legal_hold_enabled = True
        settings.save()
        invalidate_settings_cache()

        self.client.force_authenticate(user=self.employee)
        from documents.models import Document
        doc = Document.objects.create(
            owner=self.employee,
            name="Confidential.pdf",
            original_filename="Confidential.pdf",
            file_type="PDF",
            size=1024,
            sha256="e" * 64,
            storage_key=secrets.token_hex(32),
            status=Document.Status.DELETED,
        )
        response = self.client.post(f"/api/documents/{doc.id}/purge/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("legal hold", response.json().get("detail", "").lower())
