from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient as DRFAPIClient

User = get_user_model()


class APIClient(DRFAPIClient):
    def __init__(self, *args, **kwargs):
        self.tab_session_key = None
        super().__init__(*args, **kwargs)

    def request(self, **kwargs):
        public_paths = {
            reverse("auth-csrf"),
            reverse("auth-login"),
            reverse("auth-password-reset"),
            reverse("auth-password-reset-confirm"),
            reverse("auth-2fa-verify-login"),
            reverse("auth-2fa-setup-login"),
        }
        if self.tab_session_key and kwargs.get("PATH_INFO") not in public_paths:
            kwargs["HTTP_X_DOCTRUST_SESSION"] = self.tab_session_key
        response = super().request(**kwargs)
        response_data = getattr(response, "data", {})
        issued_session_key = response_data.get("tab_session_key")
        if issued_session_key:
            self.tab_session_key = issued_session_key
        if kwargs.get("PATH_INFO") == reverse("auth-logout") and response.status_code == status.HTTP_200_OK:
            self.tab_session_key = None
        return response


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "accounts.authentication.TabSessionAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        "EXCEPTION_HANDLER": "accounts.exceptions.custom_exception_handler",
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.admin_password = "SecurePassword123!"
        self.employee_password = "EmployeePassword123!"

        self.admin_user = User.objects.create_user(
            username="admin_user",
            email="admin@doctrust.local",
            password=self.admin_password,
            first_name="Admin",
            last_name="User",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )

        self.employee_user = User.objects.create_user(
            username="employee_user",
            email="employee@doctrust.local",
            password=self.employee_password,
            first_name="Employee",
            last_name="User",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
            is_staff=False,
            is_superuser=False,
        )

        self.suspended_user = User.objects.create_user(
            username="suspended_user",
            email="suspended@doctrust.local",
            password="SuspendedPass123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.SUSPENDED,
        )

        self.inactive_user = User.objects.create_user(
            username="inactive_user",
            email="inactive@doctrust.local",
            password="InactivePass123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
            is_active=False,
        )

    def _get_csrf_token(self):
        """Helper to fetch CSRF token and prime client cookies."""
        csrf_response = self.client.get(reverse("auth-csrf"))
        self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
        return csrf_response.data["csrfToken"]

    def test_csrf_endpoint_sets_cookie_and_payload(self):
        response = self.client.get(reverse("auth-csrf"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.data)
        self.assertTrue(bool(response.data["csrfToken"]))
        self.assertIn("csrftoken", self.client.cookies)
        self.assertTrue(bool(self.client.cookies["csrftoken"].value))

    def test_employee_profile_update_persists_and_returns_saved_fields(self):
        token = self._get_csrf_token()
        self.client.post(
            reverse("auth-login"),
            {
                "username": "employee_user",
                "password": self.employee_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        token = self._get_csrf_token()
        response = self.client.patch(
            reverse("auth-me"),
            {
                "name": "Updated Employee",
                "email": "updated.employee@doctrust.local",
                "role": "ADMIN",
                "status": "SUSPENDED",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["display_name"], "Updated Employee")
        self.assertEqual(response.data["email"], "updated.employee@doctrust.local")
        self.employee_user.refresh_from_db()
        self.assertEqual(self.employee_user.first_name, "Updated")
        self.assertEqual(self.employee_user.last_name, "Employee")
        self.assertEqual(self.employee_user.email, "updated.employee@doctrust.local")
        self.assertEqual(self.employee_user.role, User.Role.EMPLOYEE)
        self.assertEqual(self.employee_user.status, User.Status.ACTIVE)

        refreshed_profile = self.client.get(reverse("auth-me"))
        self.assertEqual(refreshed_profile.data["display_name"], "Updated Employee")
        self.assertEqual(refreshed_profile.data["email"], "updated.employee@doctrust.local")

    def test_employee_profile_update_rejects_duplicate_email(self):
        token = self._get_csrf_token()
        self.client.post(
            reverse("auth-login"),
            {
                "username": "employee_user",
                "password": self.employee_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        token = self._get_csrf_token()
        response = self.client.patch(
            reverse("auth-me"),
            {"name": "Employee User", "email": self.admin_user.email},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.employee_user.refresh_from_db()
        self.assertEqual(self.employee_user.email, "employee@doctrust.local")

    def test_profile_update_requires_authentication(self):
        token = self._get_csrf_token()
        response = self.client.patch(
            reverse("auth-me"),
            {"name": "Unauthorized Change", "email": "unauthorized@doctrust.local"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Role-Matched Login Tests ──────────────────────────────────────────

    def test_admin_selected_with_admin_credentials_succeeds(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "admin_user")
        self.assertEqual(response.data["role"], "ADMIN")
        self.assertNotIn("password", response.data)

        # Confirm session was established
        me_response = self.client.get(reverse("auth-me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["id"], self.admin_user.id)

    def test_admin_selected_with_employee_credentials_rejected_no_session(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "employee_user",
                "password": self.employee_password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Invalid credentials for the selected role. Please check your account type and try again.",
        )

        # Confirm NO session was created
        me_response = self.client.get(reverse("auth-me"))
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_employee_selected_with_employee_credentials_succeeds(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "employee_user",
                "password": self.employee_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "employee_user")
        self.assertEqual(response.data["role"], "EMPLOYEE")

        # Confirm session was established
        me_response = self.client.get(reverse("auth-me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["id"], self.employee_user.id)

    def test_employee_selected_with_admin_credentials_rejected_no_session(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Invalid credentials for the selected role. Please check your account type and try again.",
        )

        # Confirm NO session was created
        me_response = self.client.get(reverse("auth-me"))
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_expected_role_rejected(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expected_role", response.data.get("errors", {}))

    def test_login_invalid_expected_role_rejected(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "SUPERUSER",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_email_identifier(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "employee@doctrust.local",
                "password": self.employee_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "employee_user")

    def test_login_remember_me_options(self):
        token = self._get_csrf_token()
        response_no_rem = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "ADMIN",
                "remember_me": False,
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response_no_rem.status_code, status.HTTP_200_OK)
        from django.contrib.sessions.backends.db import SessionStore
        self.assertTrue(SessionStore(session_key=response_no_rem.data["tab_session_key"]).get_expire_at_browser_close())

        token = self._get_csrf_token()
        response_rem = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "ADMIN",
                "remember_me": True,
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response_rem.status_code, status.HTTP_200_OK)
        self.assertFalse(SessionStore(session_key=response_rem.data["tab_session_key"]).get_expire_at_browser_close())

    def test_login_rejects_invalid_password_without_account_enumeration(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": "WrongPassword999!",
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid credentials or account is inactive.")

    def test_login_rejects_nonexistent_user_with_identical_error(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "non_existent_user",
                "password": "AnyPassword123!",
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid credentials or account is inactive.")

    def test_login_rejects_suspended_account(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "suspended_user",
                "password": "SuspendedPass123!",
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data.get("suspended"))
        self.assertIn("suspended", response.data["detail"].lower())

    def test_login_rejects_inactive_account(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "inactive_user",
                "password": "InactivePass123!",
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid credentials or account is inactive.")

    def test_csrf_protection_enforced_on_login(self):
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "ADMIN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_terminates_session(self):
        token = self._get_csrf_token()
        self.client.post(
            reverse("auth-login"),
            {
                "username": "employee_user",
                "password": self.employee_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

        token = self._get_csrf_token()
        logout_res = self.client.post(reverse("auth-logout"), {}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sessions_are_tab_scoped_and_logout_does_not_affect_another_tab(self):
        first_csrf = self._get_csrf_token()
        first_login = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=first_csrf,
        )
        self.assertEqual(first_login.status_code, status.HTTP_200_OK)
        first_session_key = first_login.data["tab_session_key"]
        self.assertNotIn(settings.SESSION_COOKIE_NAME, self.client.cookies)

        second_tab = APIClient(enforce_csrf_checks=True)
        second_csrf = second_tab.get(reverse("auth-csrf")).data["csrfToken"]
        second_login = second_tab.post(
            reverse("auth-login"),
            {
                "username": "employee_user",
                "password": self.employee_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=second_csrf,
        )
        self.assertEqual(second_login.status_code, status.HTTP_200_OK)
        self.assertNotEqual(first_session_key, second_login.data["tab_session_key"])
        self.assertEqual(self.client.get(reverse("auth-me")).data["role"], "ADMIN")
        self.assertEqual(second_tab.get(reverse("auth-me")).data["role"], "EMPLOYEE")

        csrf = self._get_csrf_token()
        logout_response = self.client.post(
            reverse("auth-logout"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(second_tab.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

        cookie_only_client = DRFAPIClient()
        cookie_only_client.cookies[settings.SESSION_COOKIE_NAME] = second_login.data["tab_session_key"]
        self.assertEqual(
            cookie_only_client.get(reverse("auth-me")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_admin_only_access_control(self):
        token = self._get_csrf_token()

        # Unauthenticated -> 401
        self.assertEqual(self.client.get(reverse("auth-admin-check")).status_code, status.HTTP_401_UNAUTHORIZED)

        # Employee -> 403 Forbidden
        self.client.post(
            reverse("auth-login"),
            {
                "username": "employee_user",
                "password": self.employee_password,
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(self.client.get(reverse("auth-admin-check")).status_code, status.HTTP_403_FORBIDDEN)

        # Logout employee
        token = self._get_csrf_token()
        self.client.post(reverse("auth-logout"), {}, format="json", HTTP_X_CSRFTOKEN=token)

        # Admin -> 200 OK
        token = self._get_csrf_token()
        self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(self.client.get(reverse("auth-admin-check")).status_code, status.HTTP_200_OK)

    def test_sensitive_fields_never_exposed(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_user",
                "password": self.admin_password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        forbidden_keys = {"password", "secret", "is_superuser", "is_staff"}
        for key in forbidden_keys:
            self.assertNotIn(key, response.data)

    def test_seed_dev_users_command_refuses_when_debug_false(self):
        from django.core.management import CommandError, call_command
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_dev_users")
            self.assertIn("SECURITY GUARD", str(ctx.exception))

    def test_seed_dev_users_command_creates_and_idempotent(self):
        from django.core.management import call_command
        User.objects.filter(username__in=["admin_demo", "employee_demo"]).delete()

        with override_settings(DEBUG=True):
            call_command("seed_dev_users")
            admin_user = User.objects.get(username="admin_demo")
            employee_user = User.objects.get(username="employee_demo")

            self.assertEqual(admin_user.role, User.Role.ADMIN)
            self.assertTrue(admin_user.is_staff)
            self.assertTrue(admin_user.is_superuser)
            self.assertTrue(admin_user.check_password("AdminDemo!2026"))

            self.assertEqual(employee_user.role, User.Role.EMPLOYEE)
            self.assertFalse(employee_user.is_staff)
            self.assertFalse(employee_user.is_superuser)
            self.assertTrue(employee_user.check_password("EmployeeDemo!2026"))

            # Idempotent check
            call_command("seed_dev_users")
            self.assertEqual(User.objects.filter(username="admin_demo").count(), 1)
            self.assertEqual(User.objects.filter(username="employee_demo").count(), 1)

    def test_seed_admin_mock_data_refuses_when_debug_false(self):
        from django.core.management import CommandError, call_command
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_admin_mock_data")
            self.assertIn("SECURITY GUARD", str(ctx.exception))

    def test_seed_admin_mock_data_creates_and_idempotent(self):
        from django.core.management import call_command
        with override_settings(DEBUG=True):
            call_command("seed_admin_mock_data")
            # Verify records exist in test DB
            from documents.models import Document, Folder, DocumentShare
            from auditlog.models import SecurityAlert
            demo_usernames = [
                "sarah.jenkins", "marcus.vance", "elena.rostova", "david.kim",
                "rachel.green", "carlos.mendez", "priya.sharma", "thomas.wright",
                "aaliyah.patel", "lucas.moreau", "jessica.taylor", "nathaniel.brooks",
            ]
            self.assertEqual(User.objects.filter(username__in=demo_usernames).count(), 12)
            self.assertEqual(Folder.objects.filter(owner__username__in=demo_usernames).count(), 5)
            self.assertEqual(Document.objects.filter(owner__username__in=demo_usernames).count(), 15)
            self.assertEqual(DocumentShare.objects.filter(document__owner__username__in=demo_usernames).count(), 8)
            self.assertEqual(SecurityAlert.objects.filter(details__startswith="Demonstration notification").count(), 4)

            # Rerun and verify idempotence
            call_command("seed_admin_mock_data")
            self.assertEqual(User.objects.filter(username__in=demo_usernames).count(), 12)
            self.assertEqual(Document.objects.filter(owner__username__in=demo_usernames).count(), 15)
            self.assertEqual(DocumentShare.objects.filter(document__owner__username__in=demo_usernames).count(), 8)


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "accounts.authentication.TabSessionAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        "EXCEPTION_HANDLER": "accounts.exceptions.custom_exception_handler",
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user_password = "InitialPassword123!"
        self.user = User.objects.create_user(
            username="reset_user",
            email="reset_user@doctrust.local",
            password=self.user_password,
            first_name="Reset",
            last_name="Tester",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )
        self.suspended_user = User.objects.create_user(
            username="reset_suspended",
            email="suspended_reset@doctrust.local",
            password="SuspendedPass123!",
            role=User.Role.EMPLOYEE,
            status=User.Status.SUSPENDED,
        )
        mail.outbox = []

    def _get_csrf_token(self):
        csrf_response = self.client.get(reverse("auth-csrf"))
        return csrf_response.data["csrfToken"]

    def test_password_reset_request_returns_generic_response_for_existing_email(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-password-reset"),
            {"email": "reset_user@doctrust.local"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["detail"],
            "If an account exists for that email, password reset instructions will be sent.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password?uid=", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["reset_user@doctrust.local"])

    def test_password_reset_request_returns_identical_generic_response_for_nonexistent_email(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-password-reset"),
            {"email": "nonexistent@doctrust.local"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["detail"],
            "If an account exists for that email, password reset instructions will be sent.",
        )
        self.assertEqual(len(mail.outbox), 0)  # No email sent

    def test_password_reset_request_ineligible_user_does_not_send_email(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-password-reset"),
            {"email": "suspended_reset@doctrust.local"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_successful(self):
        token = self._get_csrf_token()
        self.client.post(
            reverse("auth-password-reset"),
            {"email": "reset_user@doctrust.local"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(len(mail.outbox), 1)

        # Extract uid and token
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)

        new_password = "BrandNewSecurePassword123!"
        token = self._get_csrf_token()
        confirm_response = self.client.post(
            reverse("auth-password-reset-confirm"),
            {
                "uid": uid,
                "token": reset_token,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertIn("Password has been reset successfully", confirm_response.data["detail"])

        # Verify old password no longer works
        self.assertIsNone(authenticate(username="reset_user", password=self.user_password))

        # Verify new password works
        authenticated_user = authenticate(username="reset_user", password=new_password)
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.id, self.user.id)

    def test_password_reset_token_invalid_after_use(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)
        new_password = "BrandNewSecurePassword123!"

        token = self._get_csrf_token()
        first_res = self.client.post(
            reverse("auth-password-reset-confirm"),
            {
                "uid": uid,
                "token": reset_token,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(first_res.status_code, status.HTTP_200_OK)

        # Second attempt with same token must fail
        token = self._get_csrf_token()
        second_res = self.client.post(
            reverse("auth-password-reset-confirm"),
            {
                "uid": uid,
                "token": reset_token,
                "new_password": "AnotherPassword456!",
                "confirm_password": "AnotherPassword456!",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(second_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid or has expired", second_res.data["detail"])

    def test_password_reset_invalid_token_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-password-reset-confirm"),
            {
                "uid": uid,
                "token": "completely-invalid-token",
                "new_password": "BrandNewSecurePassword123!",
                "confirm_password": "BrandNewSecurePassword123!",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_password_mismatch_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-password-reset-confirm"),
            {
                "uid": uid,
                "token": reset_token,
                "new_password": "Password12345!",
                "confirm_password": "PasswordDifferent999!",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data.get("errors", {}))

    def test_password_reset_password_validation_rules_enforced(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)
        token = self._get_csrf_token()
        # Too short (< 10 characters)
        response = self.client.post(
            reverse("auth-password-reset-confirm"),
            {
                "uid": uid,
                "token": reset_token,
                "new_password": "short",
                "confirm_password": "short",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Password does not meet requirements.", response.data["detail"])

    def test_password_reset_missing_fields_rejected(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-password-reset-confirm"),
            {"token": "xyz"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_no_sensitive_data_in_response(self):
        token = self._get_csrf_token()
        res_req = self.client.post(
            reverse("auth-password-reset"),
            {"email": "reset_user@doctrust.local"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertNotIn("token", res_req.data)
        self.assertNotIn("uid", res_req.data)
        self.assertNotIn("password", res_req.data)


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "accounts.authentication.TabSessionAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        "EXCEPTION_HANDLER": "accounts.exceptions.custom_exception_handler",
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    },
)
class CsrfAndOriginSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.password = "SecurePassword123!"
        self.user = User.objects.create_user(
            username="csrf_test_user",
            email="csrf_test@doctrust.local",
            password=self.password,
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )

    def _get_csrf_token(self):
        response = self.client.get(reverse("auth-csrf"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["csrfToken"]

    def test_explicit_trusted_origins_include_ports_5173_5174_5175(self):
        from django.conf import settings
        expected_ports = ["5173", "5174", "5175"]
        for port in expected_ports:
            localhost_origin = f"http://localhost:{port}"
            ip_origin = f"http://127.0.0.1:{port}"
            self.assertIn(localhost_origin, settings.CSRF_TRUSTED_ORIGINS)
            self.assertIn(ip_origin, settings.CSRF_TRUSTED_ORIGINS)
            self.assertIn(localhost_origin, settings.CORS_ALLOWED_ORIGINS)
            self.assertIn(ip_origin, settings.CORS_ALLOWED_ORIGINS)

        # Confirm no wildcards are used
        self.assertNotIn("*", settings.CSRF_TRUSTED_ORIGINS)
        self.assertNotIn("*", settings.CORS_ALLOWED_ORIGINS)

    def test_login_csrf_origin_checking_allows_localhost_5173(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "csrf_test_user",
                "password": self.password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://localhost:5173",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_csrf_origin_checking_allows_localhost_5174(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "csrf_test_user",
                "password": self.password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://localhost:5174",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_csrf_origin_checking_allows_localhost_5175(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "csrf_test_user",
                "password": self.password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://localhost:5175",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_csrf_origin_checking_rejects_untrusted_origin(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "csrf_test_user",
                "password": self.password,
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://untrusted-origin.malicious.com",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TwoFactorAuthenticationTests(TestCase):
    """
    Focused test suite for Two-Factor Authentication (TOTP + recovery codes).
    Tests enrollment, verification, login challenge enforcement, recovery code
    single-use, rate-limiting lockout, replay protection, and policy enforcement.
    """

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=False)
        self.password = "SecureTestPassword123!"

        self.user = User.objects.create_user(
            username="test_2fa_user",
            email="test_2fa@doctrust.local",
            password=self.password,
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )

        self.employee = User.objects.create_user(
            username="test_emp_user",
            email="test_emp@doctrust.local",
            password=self.password,
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )

        self.status_url = reverse("auth-2fa-status")
        self.enroll_url = reverse("auth-2fa-enroll")
        self.verify_enroll_url = reverse("auth-2fa-verify-enroll")
        self.disable_url = reverse("auth-2fa-disable")
        self.verify_login_url = reverse("auth-2fa-verify-login")
        self.setup_login_url = reverse("auth-2fa-setup-login")
        self.login_url = reverse("auth-login")

    def _enable_2fa_for_user(self, user):
        """Helper to programmatically enable 2FA and return secret and recovery codes."""
        import pyotp
        from accounts.two_factor_service import start_enrollment, verify_enrollment
        enroll_data = start_enrollment(user)
        secret = enroll_data["secret"]
        totp = pyotp.TOTP(secret)
        code = totp.now()
        recovery_codes = verify_enrollment(user, code)
        user.two_factor.last_verified_counter = 0
        user.two_factor.save(update_fields=["last_verified_counter"])
        return secret, recovery_codes

    def test_2fa_status_disabled_by_default(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["enabled"])
        self.assertFalse(data["is_enabled"])
        self.assertEqual(data["recovery_codes_remaining"], 0)

    def test_enroll_starts_and_returns_secret_and_qr(self):
        import base64
        import xml.etree.ElementTree as ET

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.enroll_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("secret", data)
        self.assertIn("provisioning_uri", data)
        self.assertIn("qr_code", data)
        self.assertIn("qr_code_svg", data)
        self.assertEqual(data["qr_code"], data["qr_code_svg"])
        self.assertTrue(data["qr_code"].startswith("data:image/svg+xml;base64,"))

        # Validate base64 payload is well-formed XML and valid SVG
        header, b64_payload = data["qr_code"].split(",", 1)
        self.assertEqual(header, "data:image/svg+xml;base64")
        svg_bytes = base64.b64decode(b64_payload)
        self.assertTrue(len(svg_bytes) > 0)

        # Parse SVG XML and verify root element and geometry
        root = ET.fromstring(svg_bytes)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn("viewBox", root.attrib)

        # Verify white background rect and QR code module path exist
        rect = root.find("{http://www.w3.org/2000/svg}rect")
        self.assertIsNotNone(rect, "SVG should contain a white background rect for high-contrast scanning")
        self.assertEqual(rect.attrib.get("fill"), "white")

        path = root.find("{http://www.w3.org/2000/svg}path")
        self.assertIsNotNone(path, "SVG should contain a path element representing the QR code modules")
        self.assertEqual(path.attrib.get("fill"), "#000000")

        # Ensure 2FA is not yet enabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_2fa_enabled)

    def test_verify_enroll_success_activates_2fa_and_creates_recovery_codes(self):
        import pyotp
        from auditlog.models import AuditEvent

        self.client.force_authenticate(user=self.user)
        enroll_resp = self.client.post(self.enroll_url)
        secret = enroll_resp.json()["secret"]

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        response = self.client.post(self.verify_enroll_url, {"code": valid_code}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("recovery_codes", data)
        self.assertEqual(len(data["recovery_codes"]), 8)

        self.user.refresh_from_db()
        self.assertTrue(self.user.has_2fa_enabled)

        # Audit event logged
        audit = AuditEvent.objects.filter(action=AuditEvent.Action.MFA_ENROLL, actor=self.user).first()
        self.assertIsNotNone(audit)

    def test_verify_enroll_invalid_code_fails(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(self.enroll_url)

        response = self.client.post(self.verify_enroll_url, {"code": "000000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_2fa_enabled)

    def test_login_enforces_2fa_challenge_when_enabled(self):
        self._enable_2fa_for_user(self.user)

        # Attempt standard password login
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
                "expected_role": "ADMIN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("mfa_required"))
        self.assertIn("mfa_token", data)

        # Verify session was NOT established: /api/auth/me/ should return 401
        me_resp = self.client.get(reverse("auth-me"))
        self.assertEqual(me_resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_login_valid_totp_authenticates_session(self):
        import pyotp
        secret, _ = self._enable_2fa_for_user(self.user)

        # 1. First factor login
        login_resp = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
                "expected_role": "ADMIN",
            },
            format="json",
        )
        mfa_token = login_resp.json()["mfa_token"]

        # 2. Second factor verification
        totp = pyotp.TOTP(secret)
        code = totp.now()

        verify_resp = self.client.post(
            self.verify_login_url,
            {"mfa_token": mfa_token, "code": code},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_resp.json()["username"], self.user.username)

        # 3. Session is now active
        me_resp = self.client.get(reverse("auth-me"))
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)

    def test_verify_login_invalid_code_fails(self):
        self._enable_2fa_for_user(self.user)
        login_resp = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password, "expected_role": "ADMIN"},
            format="json",
        )
        mfa_token = login_resp.json()["mfa_token"]

        verify_resp = self.client.post(
            self.verify_login_url,
            {"mfa_token": mfa_token, "code": "999999"},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recovery_code_single_use_and_no_reuse(self):
        _, recovery_codes = self._enable_2fa_for_user(self.user)
        test_recovery_code = recovery_codes[0]

        # Login 1 with recovery code
        login_resp = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password, "expected_role": "ADMIN"},
            format="json",
        )
        mfa_token = login_resp.json()["mfa_token"]

        verify_resp = self.client.post(
            self.verify_login_url,
            {"mfa_token": mfa_token, "code": test_recovery_code},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(verify_resp.json().get("recovery_code_used"))
        self.assertEqual(verify_resp.json().get("recovery_codes_remaining"), 7)

        # Logout
        self.client.post(reverse("auth-logout"))

        # Login 2: attempt to REUSE the same recovery code
        login_resp2 = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password, "expected_role": "ADMIN"},
            format="json",
        )
        mfa_token2 = login_resp2.json()["mfa_token"]

        verify_resp2 = self.client.post(
            self.verify_login_url,
            {"mfa_token": mfa_token2, "code": test_recovery_code},
            format="json",
        )
        self.assertEqual(verify_resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disable_2fa_requires_password_and_valid_code(self):
        import pyotp
        secret, _ = self._enable_2fa_for_user(self.user)
        self.client.force_authenticate(user=self.user)

        # 1. Bad password rejects
        totp = pyotp.TOTP(secret)
        resp1 = self.client.post(
            self.disable_url,
            {"password": "WrongPassword!", "code": totp.now()},
            format="json",
        )
        self.assertEqual(resp1.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Bad code rejects
        resp2 = self.client.post(
            self.disable_url,
            {"password": self.password, "code": "000000"},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Valid password + code succeeds
        resp3 = self.client.post(
            self.disable_url,
            {"password": self.password, "code": totp.now()},
            format="json",
        )
        self.assertEqual(resp3.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertFalse(self.user.has_2fa_enabled)
        self.assertEqual(self.user.two_factor_recovery_codes.count(), 0)

    def test_mfa_required_safe_default(self):
        from accounts.two_factor_service import is_mfa_required_for_user
        self.assertFalse(is_mfa_required_for_user(self.user))



class AdminManagementAndProfileTests(TestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        self.timezone = timezone
        self.timedelta = timedelta

        self.client = APIClient(enforce_csrf_checks=True)
        self.admin = User.objects.create_user(
            username="admin_mgr",
            email="admin_mgr@doctrust.local",
            password="AdminPassword123!",
            first_name="Super",
            last_name="Admin",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )
        self.employee = User.objects.create_user(
            username="emp_target",
            email="emp_target@doctrust.local",
            password="EmployeePassword123!",
            first_name="Target",
            last_name="Employee",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
        )

    def _get_csrf_token(self):
        resp = self.client.get(reverse("auth-csrf"))
        return resp.data["csrfToken"]

    def _auth_as_admin(self):
        token = self._get_csrf_token()
        self.client.post(
            reverse("auth-login"),
            {"username": "admin_mgr", "password": "AdminPassword123!", "expected_role": "ADMIN"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        return self._get_csrf_token()

    def test_admin_suspend_user_custom_duration_and_reason(self):
        token = self._auth_as_admin()
        url = reverse("admin-user-suspend", kwargs={"pk": self.employee.id})
        response = self.client.post(
            url,
            {"duration_hours": 48, "reason": "Investigation into abnormal download volume"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["status"], User.Status.SUSPENDED)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, User.Status.SUSPENDED)
        self.assertTrue(self.employee.is_currently_suspended)
        self.assertEqual(self.employee.suspension_reason, "Investigation into abnormal download volume")
        self.assertIsNotNone(self.employee.suspension_end)
        self.assertEqual(self.employee.suspended_by, self.admin)
        from auditlog.models import AuditEvent
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.USER_SUSPEND,
                target_id=str(self.employee.id),
                actor=self.admin,
            ).exists()
        )
        listed_employee = self.client.get(
            reverse("admin-user-list"),
            {"role": "EMPLOYEE"},
        ).data["results"][0]
        self.assertEqual(listed_employee["status"], User.Status.SUSPENDED)

        repeated_response = self.client.post(
            url,
            {"duration_hours": 48, "reason": "Repeated request"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(repeated_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.USER_SUSPEND,
                target_id=str(self.employee.id),
            ).count(),
            1,
        )

    def test_admin_unsuspend_user_early(self):
        token = self._auth_as_admin()
        # First suspend
        self.employee.status = User.Status.SUSPENDED
        self.employee.suspension_end = self.timezone.now() + self.timedelta(hours=24)
        self.employee.suspension_reason = "Temporary hold"
        self.employee.save()

        url = reverse("admin-user-unsuspend", kwargs={"pk": self.employee.id})
        response = self.client.post(url, {}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, User.Status.ACTIVE)
        self.assertFalse(self.employee.is_currently_suspended)
        from auditlog.models import AuditEvent
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.USER_ACTIVATE,
                target_id=str(self.employee.id),
                metadata__reason="administrative_reactivation",
            ).exists()
        )
        self.assertIsNone(self.employee.suspension_end)
        self.assertFalse(self.employee.suspension_reason)

    def test_indefinite_suspension_revokes_sessions_until_employee_logs_in_again(self):
        employee_client = APIClient(enforce_csrf_checks=True)
        employee_csrf = employee_client.get(reverse("auth-csrf")).data["csrfToken"]
        login_response = employee_client.post(
            reverse("auth-login"),
            {
                "username": "emp_target",
                "password": "EmployeePassword123!",
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=employee_csrf,
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(employee_client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

        admin_token = self._auth_as_admin()
        suspend_url = reverse("admin-user-suspend", kwargs={"pk": self.employee.id})
        suspend_response = self.client.post(
            suspend_url,
            {"reason": "Manual review"},
            format="json",
            HTTP_X_CSRFTOKEN=admin_token,
        )
        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(suspend_response.data["user"]["status"], User.Status.SUSPENDED)
        self.assertIsNone(suspend_response.data["user"]["suspension_end"])

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, User.Status.SUSPENDED)
        self.assertIsNone(self.employee.suspension_end)
        self.assertEqual(employee_client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            employee_client.get(reverse("document-list-create")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.get(reverse("admin-user-list")).status_code,
            status.HTTP_200_OK,
        )

        relogin_csrf = employee_client.get(reverse("auth-csrf")).data["csrfToken"]
        rejected_login = employee_client.post(
            reverse("auth-login"),
            {
                "username": "emp_target",
                "password": "EmployeePassword123!",
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=relogin_csrf,
        )
        self.assertEqual(rejected_login.status_code, status.HTTP_403_FORBIDDEN)

        unsuspend_response = self.client.post(
            reverse("admin-user-unsuspend", kwargs={"pk": self.employee.id}),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=admin_token,
        )
        self.assertEqual(unsuspend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(unsuspend_response.data["user"]["status"], User.Status.ACTIVE)
        self.assertEqual(employee_client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)

        relogin_csrf = employee_client.get(reverse("auth-csrf")).data["csrfToken"]
        successful_login = employee_client.post(
            reverse("auth-login"),
            {
                "username": "emp_target",
                "password": "EmployeePassword123!",
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=relogin_csrf,
        )
        self.assertEqual(successful_login.status_code, status.HTTP_200_OK)
        self.assertEqual(successful_login.data["role"], User.Role.EMPLOYEE)

    def test_suspension_auto_expiry_allows_login(self):
        # Set user as suspended with expiration 1 hour in the past
        self.employee.status = User.Status.SUSPENDED
        self.employee.suspension_end = self.timezone.now() - self.timedelta(hours=1)
        self.employee.suspension_reason = "Past suspension"
        self.employee.save()

        # Attempting login should auto-expire the suspension and succeed
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("auth-login"),
            {"username": "emp_target", "password": "EmployeePassword123!", "expected_role": "EMPLOYEE"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, User.Status.ACTIVE)
        self.assertFalse(self.employee.is_currently_suspended)
        from auditlog.models import AuditEvent
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.USER_ACTIVATE,
                target_id=str(self.employee.id),
                metadata__reason="automatic_suspension_expiry",
            ).exists()
        )

    def test_authenticate_rejects_suspended_account(self):
        self.employee.status = User.Status.SUSPENDED
        self.employee.save(update_fields=["status"])

        self.assertIsNone(
            authenticate(
                username="emp_target",
                password="EmployeePassword123!",
            )
        )

    def test_admin_cannot_suspend_themselves(self):
        token = self._auth_as_admin()
        url = reverse("admin-user-suspend", kwargs={"pk": self.admin.id})
        response = self.client.post(
            url,
            {"duration_hours": 24, "reason": "Self suspension test"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_suspend_another_administrator(self):
        other_admin = User.objects.create_user(
            username="other_admin",
            email="other_admin@doctrust.local",
            password="OtherAdminPassword123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )
        token = self._auth_as_admin()
        response = self.client.post(
            reverse("admin-user-suspend", kwargs={"pk": other_admin.id}),
            {"duration_hours": 24, "reason": "Employee-only action test"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        other_admin.refresh_from_db()
        self.assertEqual(other_admin.status, User.Status.ACTIVE)

    def test_admin_cannot_reactivate_an_administrator_through_employee_action(self):
        other_admin = User.objects.create_user(
            username="suspended_admin",
            email="suspended_admin@doctrust.local",
            password="SuspendedAdminPassword123!",
            role=User.Role.ADMIN,
            status=User.Status.SUSPENDED,
            suspension_reason="Separate administrator workflow",
        )
        token = self._auth_as_admin()

        response = self.client.post(
            reverse("admin-user-unsuspend", kwargs={"pk": other_admin.id}),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        other_admin.refresh_from_db()
        self.assertEqual(other_admin.status, User.Status.SUSPENDED)

    def test_suspension_blocks_an_existing_authenticated_session(self):
        employee_client = APIClient(enforce_csrf_checks=True)
        csrf_token = employee_client.get(reverse("auth-csrf")).data["csrfToken"]
        login_response = employee_client.post(
            reverse("auth-login"),
            {
                "username": "emp_target",
                "password": "EmployeePassword123!",
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        admin_token = self._auth_as_admin()
        suspend_response = self.client.post(
            reverse("admin-user-suspend", kwargs={"pk": self.employee.id}),
            {"duration_hours": 24, "reason": "Access review"},
            format="json",
            HTTP_X_CSRFTOKEN=admin_token,
        )
        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(employee_client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            employee_client.get(reverse("document-list-create")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        new_employee_client = APIClient(enforce_csrf_checks=True)
        new_csrf_token = new_employee_client.get(reverse("auth-csrf")).data["csrfToken"]
        login_response = new_employee_client.post(
            reverse("auth-login"),
            {
                "username": "emp_target",
                "password": "EmployeePassword123!",
                "expected_role": "EMPLOYEE",
            },
            format="json",
            HTTP_X_CSRFTOKEN=new_csrf_token,
        )
        self.assertEqual(login_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_suspend_an_account(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            reverse("admin-user-suspend", kwargs={"pk": self.admin.id}),
            {"duration_hours": 24, "reason": "Not authorized"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        unsuspend_response = self.client.post(
            reverse("admin-user-unsuspend", kwargs={"pk": self.employee.id}),
            {},
            format="json",
        )
        self.assertEqual(unsuspend_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_suspension_requires_valid_duration_and_reason(self):
        token = self._auth_as_admin()
        response = self.client.post(
            reverse("admin-user-suspend", kwargs={"pk": self.employee.id}),
            {"duration_hours": 0, "reason": " "},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, User.Status.ACTIVE)

    def test_admin_user_list_separates_roles_and_supports_search(self):
        User.objects.create_user(
            username="second_admin",
            email="second_admin@doctrust.local",
            password="AdminPassword123!",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )
        self._auth_as_admin()

        admins = self.client.get(reverse("admin-user-list"), {"role": "ADMIN", "page_size": 8})
        employees = self.client.get(
            reverse("admin-user-list"),
            {"role": "EMPLOYEE", "search": "Target", "page_size": 8},
        )
        self.assertEqual(admins.status_code, status.HTTP_200_OK)
        self.assertEqual(admins.data["total"], 2)
        self.assertTrue(all(user["role"] == User.Role.ADMIN for user in admins.data["results"]))
        self.assertEqual(employees.status_code, status.HTTP_200_OK)
        self.assertEqual(employees.data["total"], 1)
        self.assertEqual(employees.data["results"][0]["username"], self.employee.username)

    def test_admin_login_session_authorizes_user_management_list(self):
        csrf_token = self._get_csrf_token()
        login_response = self.client.post(
            reverse("auth-login"),
            {
                "username": "admin_mgr",
                "password": "AdminPassword123!",
                "expected_role": "ADMIN",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("tab_session_key", login_response.data)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, self.client.cookies)

        user_list_response = self.client.get(
            reverse("admin-user-list"),
            {"role": "ADMIN", "page": 1, "pageSize": 8},
        )
        self.assertEqual(user_list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_list_response.data["total"], 1)
        user_data = user_list_response.data["results"][0]
        self.assertEqual(user_data["id"], self.admin.id)
        self.assertEqual(user_data["role"], User.Role.ADMIN)
        self.assertIn("status", user_data)
        self.assertIsNotNone(user_data["last_login"])

        unauthenticated_client = APIClient(enforce_csrf_checks=True)
        unauthenticated_response = unauthenticated_client.get(reverse("admin-user-list"))
        self.assertEqual(unauthenticated_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_update_via_patch_me(self):
        token = self._auth_as_admin()
        response = self.client.patch(
            reverse("auth-me"),
            {"name": "Alexander Pierce", "email": "alex.pierce@doctrust.local"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, "Alexander")
        self.assertEqual(self.admin.last_name, "Pierce")
        self.assertEqual(self.admin.email, "alex.pierce@doctrust.local")

    def test_password_change_flow(self):
        token = self._auth_as_admin()
        url = reverse("auth-password-change")

        # 1. Incorrect current password rejected
        bad_resp = self.client.post(
            url,
            {
                "current_password": "WrongPassword123!",
                "new_password": "NewSecurePassword456!",
                "confirm_password": "NewSecurePassword456!",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(bad_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Mismatched confirmation rejected
        token = self._get_csrf_token()
        mismatch_resp = self.client.post(
            url,
            {
                "current_password": "AdminPassword123!",
                "new_password": "NewSecurePassword456!",
                "confirm_password": "DifferentPassword456!",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(mismatch_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Valid change succeeds
        token = self._get_csrf_token()
        good_resp = self.client.post(
            url,
            {
                "current_password": "AdminPassword123!",
                "new_password": "NewSecurePassword456!",
                "confirm_password": "NewSecurePassword456!",
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(good_resp.status_code, status.HTTP_200_OK)

        # Verify old password no longer works and new password works
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.check_password("AdminPassword123!"))
        self.assertTrue(self.admin.check_password("NewSecurePassword456!"))
