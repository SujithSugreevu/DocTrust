"""Shared safety checks for explicit DocTrust demonstration-data seeding."""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import CommandError


DEMO_MODE_ENV = "DOCTRUST_DEMO_MODE"
EPHEMERAL_DEMO_FILES_ENV = "DOCTRUST_DEMO_EPHEMERAL_FILES"


def add_demo_seed_arguments(parser):
    """Add the production safety switch shared by demo-data commands."""
    parser.add_argument(
        "--allow-production-demo",
        action="store_true",
        help="Allow deliberate production demo seeding only when DOCTRUST_DEMO_MODE is enabled.",
    )
    parser.add_argument(
        "--allow-ephemeral-demo-files",
        action="store_true",
        help=(
            "Allow fictional demo files to be regenerated under an ephemeral storage root; "
            "requires DOCTRUST_DEMO_EPHEMERAL_FILES=1 and the production demo guard."
        ),
    )


def is_demo_mode_enabled():
    return str(os.environ.get(DEMO_MODE_ENV, "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def is_ephemeral_demo_files_enabled():
    return str(os.environ.get(EPHEMERAL_DEMO_FILES_ENV, "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def is_remote_database_configured():
    """Detect remote/production database configuration even when DEBUG is true."""
    if "test" in sys.argv:
        return False

    if str(os.environ.get("NEON_BRANCH", "")).strip().lower() == "production":
        return True

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        return False

    hostname = urlparse(database_url).hostname or ""
    return hostname.lower() not in {"localhost", "127.0.0.1", "::1"}


def ensure_demo_seed_allowed(options):
    """Refuse implicit production fixture writes."""
    allow_production = bool(options.get("allow_production_demo"))
    demo_mode_enabled = is_demo_mode_enabled()
    if allow_production and not demo_mode_enabled:
        raise CommandError(
            "SECURITY GUARD: --allow-production-demo requires DOCTRUST_DEMO_MODE=1."
        )
    if not settings.DEBUG or is_remote_database_configured():
        if allow_production and demo_mode_enabled:
            return
        raise CommandError(
            "SECURITY GUARD: demonstration data seeding is disabled for a remote or "
            "DEBUG=False database. Enable DOCTRUST_DEMO_MODE temporarily and pass "
            "--allow-production-demo for a deliberate one-time seed."
        )
    if not allow_production:
        return


def ensure_demo_storage_is_persistent(options=None):
    """
    Validate demo-file storage before a seed.

    Real uploads must use persistent storage. A deliberately enabled demo-only
    mode may use an ephemeral root because every seeded command repairs only
    fictional demo files whose database records already identify them.
    """
    options = options or {}
    if settings.DEBUG and not is_remote_database_configured():
        return False

    configured_root = os.environ.get("DOCUMENT_STORAGE_ROOT", "").strip()
    root = Path(getattr(settings, "DOCUMENT_STORAGE_ROOT", "")).resolve()
    normalized = root.as_posix().rstrip("/")
    if not configured_root or normalized in {"/tmp", "/var/tmp"} or normalized.startswith(("/tmp/", "/var/tmp/")):
        ephemeral_demo_mode = (
            bool(options.get("allow_production_demo"))
            and bool(options.get("allow_ephemeral_demo_files"))
            and is_demo_mode_enabled()
            and is_ephemeral_demo_files_enabled()
        )
        if ephemeral_demo_mode:
            return True
        raise CommandError(
            "SECURITY GUARD: configure DOCUMENT_STORAGE_ROOT on persistent storage before "
            "seeding document files. For fictional demo files only, explicitly enable "
            "DOCTRUST_DEMO_MODE=1, DOCTRUST_DEMO_EPHEMERAL_FILES=1 and pass both "
            "--allow-production-demo and --allow-ephemeral-demo-files."
        )

    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise CommandError(
            "DOCUMENT_STORAGE_ROOT is not writable by the deployment runtime."
        ) from exc
    if not os.access(root, os.W_OK):
        raise CommandError("DOCUMENT_STORAGE_ROOT is not writable by the deployment runtime.")
    return False
