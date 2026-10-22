from django.urls import path
from systemsettings.views import SystemSettingsDetailView, SystemSettingsResetView

urlpatterns = [
    path("", SystemSettingsDetailView.as_view(), name="system-settings"),
    path("reset/", SystemSettingsResetView.as_view(), name="system-settings-reset"),
]
