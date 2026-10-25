from django.urls import path
from accounts import views

urlpatterns = [
    path("csrf/", views.CSRFView.as_view(), name="auth-csrf"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.CurrentUserView.as_view(), name="auth-me"),
    path("session/", views.CurrentUserView.as_view(), name="auth-session"),
    path("admin-check/", views.AdminOnlyCheckView.as_view(), name="auth-admin-check"),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("password-change/", views.PasswordChangeView.as_view(), name="auth-password-change"),
    path("profile/", views.CurrentUserView.as_view(), name="auth-profile"),
    # Two-Factor Authentication routes
    path("2fa/status/", views.TwoFactorStatusView.as_view(), name="auth-2fa-status"),
    path("2fa/enroll/", views.TwoFactorEnrollView.as_view(), name="auth-2fa-enroll"),
    path("2fa/verify-enroll/", views.TwoFactorVerifyEnrollView.as_view(), name="auth-2fa-verify-enroll"),
    path("2fa/disable/", views.TwoFactorDisableView.as_view(), name="auth-2fa-disable"),
    path("2fa/verify-login/", views.TwoFactorLoginVerifyView.as_view(), name="auth-2fa-verify-login"),
    path("2fa/setup-login/", views.TwoFactorLoginSetupView.as_view(), name="auth-2fa-setup-login"),
]
