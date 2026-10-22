from django.contrib import admin
from systemsettings.models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """Read-only Django admin view for the singleton settings row."""

    list_display = ("app_name", "maintenance_mode", "updated_at")

    def has_add_permission(self, request):
        # Singleton — prevent creating additional rows
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
