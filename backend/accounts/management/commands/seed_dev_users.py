"""
DocTrust Development Seeding Command.

This management command creates local development-only test accounts (Administrator & Employee)
for local testing of DocTrust authentication and role authorization flows.

SECURITY CONSTRAINTS:
- STRICTLY disabled in production: execution halts with CommandError if settings.DEBUG is False.
- Passwords are encrypted via Django's PBKDF2/Argon2 password hasher; plaintext is never stored.
- Idempotent: existing accounts are NOT overwritten, reset, or altered in any way.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds local development test accounts (admin_demo and employee_demo). Local DEBUG=True environments only."

    def handle(self, *args, **options):
        # 1. Strict guard: Never execute in production
        if not settings.DEBUG:
            raise CommandError(
                "SECURITY GUARD: 'seed_dev_users' is strictly restricted to local development "
                "environments where DEBUG=True. Refusing to run."
            )

        self.stdout.write("Checking local development test accounts...")

        dev_accounts = [
            {
                "username": "admin_demo",
                "email": "admin_demo@doctrust.local",
                "password": "AdminDemo!2026",
                "role": User.Role.ADMIN,
                "status": User.Status.ACTIVE,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "Demo",
            },
            {
                "username": "employee_demo",
                "email": "employee_demo@doctrust.local",
                "password": "EmployeeDemo!2026",
                "role": User.Role.EMPLOYEE,
                "status": User.Status.ACTIVE,
                "is_staff": False,
                "is_superuser": False,
                "first_name": "Employee",
                "last_name": "Demo",
            },
        ]

        created_count = 0
        skipped_count = 0

        for account in dev_accounts:
            username = account["username"]
            existing = User.objects.filter(username=username).first()

            if existing:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[-] Account '{username}' already exists (ID: {existing.id}, Role: {existing.role}, Status: {existing.status}). "
                        f"Skipped without modification to preserve existing credentials and permissions. "
                        f"To safely rotate its password, run: python manage.py changepassword {username}"
                    )
                )
            else:
                User.objects.create_user(
                    username=username,
                    email=account["email"],
                    password=account["password"],
                    role=account["role"],
                    status=account["status"],
                    is_staff=account["is_staff"],
                    is_superuser=account["is_superuser"],
                    first_name=account["first_name"],
                    last_name=account["last_name"],
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[+] Created local development account: '{username}' (Role: {account['role']}, Status: {account['status']})"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding completed: {created_count} created, {skipped_count} existing accounts preserved."
            )
        )
