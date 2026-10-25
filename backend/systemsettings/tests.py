import json
import time
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from auditlog.models import AuditEvent
from systemsettings.models import SystemSettings
from systemsettings.services import invalidate_settings_cache
from systemsettings.middleware import SessionIdleTimeoutMiddleware, SESSION_IDLE_TIMEOUT_SECONDS

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
        self.assertEqual(settings.failed_login_limit, 5)

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
        payload = {"app_name": "DocTrust Enterprise", "failed_login_limit": 8}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["app_name"], "DocTrust Enterprise")
        self.assertEqual(response.json()["failed_login_limit"], 8)

        # Verify audit event was logged
        audit = AuditEvent.objects.filter(action=AuditEvent.Action.SYSTEM_SETTINGS_UPDATE).order_by("-id").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin_user)
        self.assertIn("app_name", audit.metadata.get("changed_fields", ""))

    def test_patch_rejects_invalid_values(self):
        self.client.force_authenticate(user=self.admin_user)
        # failed_login_limit must be >= 3
        payload = {"failed_login_limit": 1}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("failed_login_limit", response.json())

    def test_patch_rejects_unknown_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"unknown_secret_hack": "malicious"}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_rejects_removed_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"maintenance_mode": True}
        response = self.client.patch(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.json())

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


class SessionIdleTimeoutMiddlewareTestCase(TestCase):
    """Test SessionIdleTimeoutMiddleware behavior."""

    def setUp(self):
        self.middleware = SessionIdleTimeoutMiddleware(get_response=lambda r: None)

    def test_active_session_not_flushed(self):
        class DummyRequest:
            def __init__(self, user):
                self.user = user
                self.session = {"_last_activity": time.time() - 60}

        user = UserModel.objects.create_user(
            username="idle_test",
            email="idle@doctrust.local",
            password="SecurePassword123!",
        )
        request = DummyRequest(user)
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertIn("_last_activity", request.session)

    def test_expired_session_flushed(self):
        flushed = []

        class DummySession(dict):
            def flush(self):
                flushed.append(True)
                self.clear()

        class DummyRequest:
            def __init__(self, user):
                self.user = user
                self.session = DummySession({"_last_activity": time.time() - (SESSION_IDLE_TIMEOUT_SECONDS + 10)})

        user = UserModel.objects.create_user(
            username="idle_test2",
            email="idle2@doctrust.local",
            password="SecurePassword123!",
        )
        request = DummyRequest(user)
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 401)
        self.assertTrue(len(flushed) > 0)
