"""Create or repair the two explicitly requested DocTrust demo accounts.

The command never contains a password literal. Passwords are supplied through
one-time environment variables or hidden interactive prompts, then passed to
Django's password hasher. Existing credentials are preserved unless
``--reset-passwords`` is explicitly supplied.
"""

import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.management.commands.demo_seed_support import ensure_demo_seed_allowed


User = get_user_model()

PASSWORD_ENV_BY_USERNAME = {
    "admin_demo": "DOCTRUST_DEMO_ADMIN_PASSWORD",
    "employee_demo": "DOCTRUST_DEMO_EMPLOYEE_PASSWORD",
}

DEMO_ACCOUNTS = (
    {
        "username": "admin_demo",
        "email": "admin_demo@doctrust.local",
        "role": User.Role.ADMIN,
        "first_name": "Admin",
        "last_name": "Demo",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "employee_demo",
        "email": "employee_demo@doctrust.local",
        "role": User.Role.EMPLOYEE,
        "first_name": "Employee",
        "last_name": "Demo",
        "is_staff": False,
        "is_superuser": False,
    },
)

class Command(BaseCommand):
    help = (
        "Create or repair the admin_demo and employee_demo accounts. "
        "Passwords must be supplied explicitly; existing passwords are preserved by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Explicitly replace existing demo passwords from the supplied secret values.",
        )
        parser.add_argument(
            "--prompt-for-passwords",
            action="store_true",
            help="Read required passwords interactively without echoing them.",
        )
        parser.add_argument(
            "--allow-production-demo",
            action="store_true",
            help="Allow a one-time production repair only when DOCTRUST_DEMO_MODE is enabled.",
        )

    def handle(self, *args, **options):
        self._enforce_environment_guard(options)

        usernames = [account["username"] for account in DEMO_ACCOUNTS]
        existing_users = {
            user.username: user
            for user in User.objects.filter(username__in=usernames)
        }
        password_values = self._get_required_passwords(
            existing_users,
            reset_passwords=options["reset_passwords"],
            prompt_for_passwords=options["prompt_for_passwords"],
        )

        created_count = 0
        repaired_count = 0
        reset_count = 0
        preserved_count = 0

        with transaction.atomic():
            for account in DEMO_ACCOUNTS:
                username = account["username"]
                user = existing_users.get(username)
                password = password_values.get(username)

                if user is None:
                    User.objects.create_user(
                        username=username,
                        email=account["email"],
                        password=password,
                        role=account["role"],
                        status=User.Status.ACTIVE,
                        is_active=True,
                        is_staff=account["is_staff"],
                        is_superuser=account["is_superuser"],
                        first_name=account["first_name"],
                        last_name=account["last_name"],
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created {account['role'].lower()} demo account '{username}'."
                        )
                    )
                    continue

                update_fields = []
                if user.role != account["role"]:
                    user.role = account["role"]
                    update_fields.append("role")
                if user.status != User.Status.ACTIVE:
                    user.status = User.Status.ACTIVE
                    update_fields.append("status")
                if not user.is_active:
                    user.is_active = True
                    update_fields.append("is_active")

                if user.status == User.Status.ACTIVE:
                    for field in ("suspended_at", "suspension_end", "suspension_reason", "suspended_by"):
                        if getattr(user, field):
                            setattr(user, field, None if field != "suspension_reason" else "")
                            update_fields.append(field)

                if password is not None:
                    user.set_password(password)
                    update_fields.append("password")
                    reset_count += 1

                if update_fields:
                    user.save(update_fields=sorted(set(update_fields)))
                    repaired_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Repaired '{username}' role/status; credential changes applied only when explicitly requested."
                        )
                    )
                else:
                    preserved_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Preserved existing '{username}' account and password."
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo account repair completed: "
                f"{created_count} created, {repaired_count} repaired, "
                f"{reset_count} passwords explicitly reset, {preserved_count} preserved."
            )
        )

    def _enforce_environment_guard(self, options):
        ensure_demo_seed_allowed(options)

    def _get_required_passwords(self, existing_users, reset_passwords, prompt_for_passwords):
        required_usernames = [
            account["username"]
            for account in DEMO_ACCOUNTS
            if account["username"] not in existing_users or reset_passwords
        ]
        passwords = {}

        for username in required_usernames:
            env_name = PASSWORD_ENV_BY_USERNAME[username]
            if prompt_for_passwords:
                password = getpass.getpass(f"Password for {username}: ")
            else:
                password = os.environ.get(env_name)

            if password is None or password == "":
                raise CommandError(
                    f"No password supplied for {username}. Set {env_name} temporarily "
                    "or pass --prompt-for-passwords."
                )

            try:
                validate_password(password, user=existing_users.get(username))
            except ValidationError as exc:
                raise CommandError(
                    f"The supplied password for {username} does not satisfy the configured password policy."
                ) from exc
            passwords[username] = password

        return passwords
