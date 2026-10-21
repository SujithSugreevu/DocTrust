"""
URL configuration for DocTrust backend.
"""
from django.contrib import admin
from django.urls import include, path
from doctrust.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health_check"),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("documents.urls")),
]
