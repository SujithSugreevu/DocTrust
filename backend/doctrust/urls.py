"""
URL configuration for DocTrust backend.
"""
from django.contrib import admin
from django.urls import include, path
from doctrust.views import health_check
from accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health_check"),
    path("api/auth/", include("accounts.urls")),
    path("api/admin/users/", account_views.AdminUserListView.as_view(), name="admin-user-list"),
    path("api/admin/users/<int:pk>/", account_views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("api/admin/users/<int:pk>/suspend/", account_views.AdminUserSuspendView.as_view(), name="admin-user-suspend"),
    path("api/admin/users/<int:pk>/unsuspend/", account_views.AdminUserUnsuspendView.as_view(), name="admin-user-unsuspend"),
    path("api/admin/system-settings/", include("systemsettings.urls")),
    path("api/", include("documents.urls")),
    path("api/audit/", include("auditlog.urls")),
]

