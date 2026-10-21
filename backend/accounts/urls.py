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
]
