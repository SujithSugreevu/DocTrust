from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.SessionAuthentication",
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
        self.assertTrue(self.client.session.get_expire_at_browser_close())

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
        self.assertFalse(self.client.session.get_expire_at_browser_close())

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
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid credentials or account is inactive.")

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


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.SessionAuthentication",
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
            "rest_framework.authentication.SessionAuthentication",
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

