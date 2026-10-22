from rest_framework import serializers
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
            "display_name",
            "role",
            "status",
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

