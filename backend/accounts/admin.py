from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User, UserTwoFactor, TwoFactorRecoveryCode


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


@admin.register(UserTwoFactor)
class UserTwoFactorAdmin(admin.ModelAdmin):
    list_display = ("user", "is_enabled", "enabled_at", "failed_attempts", "lockout_until")
    list_filter = ("is_enabled",)
    readonly_fields = ("secret", "pending_secret", "last_verified_counter", "pending_created_at")


@admin.register(TwoFactorRecoveryCode)
class TwoFactorRecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "is_used", "used_at", "created_at")
    list_filter = ("is_used",)
    readonly_fields = ("code_hash",)
