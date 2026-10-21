from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "status", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "status", "is_staff", "is_superuser", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("DocTrust Attributes", {"fields": ("role", "status")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("DocTrust Attributes", {"fields": ("email", "role", "status")}),
    )
