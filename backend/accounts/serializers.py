from rest_framework import serializers
from django.utils import timezone
from accounts.models import User


class LoginSerializer(serializers.Serializer):
    """
    Serializer for authentication request accepting username/email, password,
    remember_me option, and mandatory expected_role validation.
    """
    username = serializers.CharField(
        required=True,
        trim_whitespace=True,
        error_messages={"required": "Username or email is required."}
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": "Password is required."}
    )
    expected_role = serializers.ChoiceField(
        choices=User.Role.choices,
        required=True,
        error_messages={
            "required": "Expected role is required.",
            "invalid_choice": "Invalid expected role choice."
        }
    )
    remember_me = serializers.BooleanField(required=False, default=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for initiating a secure password-reset email request.
    """
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email address is required.",
            "invalid": "Enter a valid email address.",
        }
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming a password reset using uid and cryptographic token.
    """
    uid = serializers.CharField(
        required=True,
        error_messages={"required": "User identifier is required."}
    )
    token = serializers.CharField(
        required=True,
        error_messages={"required": "Reset token is required."}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": "New password is required."}
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": "Password confirmation is required."}
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    Public-safe representation of the authenticated User.
    Excludes sensitive fields (passwords, tokens, internal permissions, TOTP secrets).
    """
    display_name = serializers.SerializerMethodField()
    two_factor_enabled = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "status",
            "suspended_at",
            "suspension_end",
            "suspension_reason",
            "date_joined",
            "last_login",
            "two_factor_enabled",
        ]
        read_only_fields = fields

    def get_display_name(self, obj):
        full_name = obj.get_full_name()
        return full_name if full_name else obj.username

    def get_two_factor_enabled(self, obj):
        return obj.has_2fa_enabled


class ProfileUpdateSerializer(serializers.Serializer):
    """Serializer for updating current user's profile information."""
    name = serializers.CharField(required=True, allow_blank=False, max_length=150)
    email = serializers.EmailField(required=True)

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Full name cannot be blank.")
        return name

    def validate_email(self, value):
        user = self.context.get("request").user
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return email


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for authenticated password change with current password confirmation."""
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": "Current password is required."}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        min_length=8,
        error_messages={"required": "New password is required."}
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": "Password confirmation is required."}
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
        return attrs


class UserSuspendSerializer(serializers.Serializer):
    """Serializer for administrative user suspension with custom duration and reason."""
    duration_days = serializers.IntegerField(required=False, min_value=1, max_value=365)
    duration_hours = serializers.IntegerField(required=False, min_value=1, max_value=8760)
    suspension_end = serializers.DateTimeField(required=False)
    reason = serializers.CharField(required=True, allow_blank=False, max_length=1000)

    def validate(self, attrs):
        duration_fields = ("duration_days", "duration_hours", "suspension_end")
        supplied_durations = [field for field in duration_fields if field in attrs]
        if len(supplied_durations) > 1:
            raise serializers.ValidationError(
                "Provide no more than one suspension duration."
            )
        if attrs.get("suspension_end") and attrs["suspension_end"] <= timezone.now():
            raise serializers.ValidationError(
                {"suspension_end": "Suspension expiry must be in the future."}
            )
        attrs["reason"] = attrs["reason"].strip()
        if not attrs["reason"]:
            raise serializers.ValidationError({"reason": "A suspension reason is required."})
        return attrs


class AdminUserCreateSerializer(serializers.Serializer):
    """Serializer for administrator creating a new user account."""
    name = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.EMPLOYEE)
    password = serializers.CharField(required=False, allow_blank=True, min_length=8)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return email


class AdminUserUpdateSerializer(serializers.Serializer):
    """Serializer for administrator editing user details."""
    name = serializers.CharField(required=False, max_length=150)
    email = serializers.EmailField(required=False)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)

    def validate_email(self, value):
        user_id = self.context.get("user_id")
        email = value.strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if user_id:
            qs = qs.exclude(pk=user_id)
        if qs.exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return email


class TwoFactorVerifyEnrollSerializer(serializers.Serializer):
    """Serializer for verifying code during 2FA enrollment."""
    code = serializers.CharField(
        required=True,
        trim_whitespace=True,
        min_length=6,
        max_length=16,
        error_messages={"required": "Verification code is required."}
    )


class TwoFactorDisableSerializer(serializers.Serializer):
    """Serializer for disabling 2FA requiring password and valid code."""
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": "Current password is required."}
    )
    code = serializers.CharField(
        required=True,
        trim_whitespace=True,
        min_length=6,
        max_length=16,
        error_messages={"required": "Verification code or recovery code is required."}
    )


class TwoFactorLoginVerifySerializer(serializers.Serializer):
    """Serializer for verifying second factor during login."""
    mfa_token = serializers.CharField(
        required=True,
        trim_whitespace=True,
        error_messages={"required": "Login challenge token is required."}
    )
    code = serializers.CharField(
        required=True,
        trim_whitespace=True,
        min_length=6,
        max_length=16,
        error_messages={"required": "Verification code or recovery code is required."}
    )


class TwoFactorLoginSetupSerializer(serializers.Serializer):
    """Serializer for completing mandatory 2FA enrollment during login."""
    mfa_token = serializers.CharField(
        required=True,
        trim_whitespace=True,
        error_messages={"required": "Login challenge token is required."}
    )
    code = serializers.CharField(
        required=True,
        trim_whitespace=True,
        min_length=6,
        max_length=16,
        error_messages={"required": "Verification code is required."}
    )
