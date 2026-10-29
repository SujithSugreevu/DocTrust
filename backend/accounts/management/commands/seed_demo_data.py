"""Explicit, idempotent orchestration for the complete DocTrust demo dataset."""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.management.commands.demo_seed_support import (
    add_demo_seed_arguments,
    ensure_demo_seed_allowed,
    ensure_demo_storage_is_persistent,
)


class Command(BaseCommand):
    help = (
        "Seed missing DocTrust demonstration users, folders, documents, shares, "
        "audit events, notifications, and security alerts."
    )

    def add_arguments(self, parser):
        add_demo_seed_arguments(parser)
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Explicitly rotate the two primary demo passwords from secret inputs.",
        )
        parser.add_argument(
            "--prompt-for-passwords",
            action="store_true",
            help="Read required primary demo passwords interactively without echoing them.",
        )

    def handle(self, *args, **options):
        ensure_demo_seed_allowed(options)
        ephemeral_demo_files = ensure_demo_storage_is_persistent(options)

        call_command(
            "seed_dev_users",
            allow_production_demo=options["allow_production_demo"],
            reset_passwords=options["reset_passwords"],
            prompt_for_passwords=options["prompt_for_passwords"],
        )
        call_command(
            "seed_admin_mock_data",
            allow_production_demo=options["allow_production_demo"],
            allow_ephemeral_demo_files=options["allow_ephemeral_demo_files"],
        )
        call_command(
            "seed_employee_mock_data",
            allow_production_demo=options["allow_production_demo"],
            allow_ephemeral_demo_files=options["allow_ephemeral_demo_files"],
        )
        call_command(
            "seed_demo_scale",
            allow_production_demo=options["allow_production_demo"],
            allow_ephemeral_demo_files=options["allow_ephemeral_demo_files"],
        )

        if ephemeral_demo_files:
            self.stdout.write(
                self.style.WARNING(
                    "Ephemeral demo-file mode enabled: only fictional demo files may be "
                    "regenerated; PostgreSQL records and real uploads are preserved."
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                "DocTrust demonstration data seed completed. Existing records were preserved."
            )
        )
