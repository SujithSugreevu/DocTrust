"""
Service layer for system settings.

Provides cached access to the singleton SystemSettings row and
real system health checks (DB connectivity, storage directory).
"""

import logging
import os
from functools import lru_cache

from django.db import connection

logger = logging.getLogger("systemsettings")

# Module-level cache. Invalidated explicitly when settings change.
_settings_cache = None


def get_system_settings():
    """
    Return the singleton SystemSettings instance.

    Uses a simple module-level cache that is invalidated on every PATCH/reset.
    Thread-safe because Django's ORM calls are thread-safe and the worst case
    is two concurrent calls both hitting the DB once.
    """
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache

    from systemsettings.models import SystemSettings
    obj = SystemSettings.load()
    _settings_cache = obj
    return obj


def invalidate_settings_cache():
    """Clear the cached settings so the next call to get_system_settings() hits the DB."""
    global _settings_cache
    _settings_cache = None


def get_system_health():
    """
    Return a dictionary of real system health indicators.

    Reports:
    - database: connectivity via SELECT 1
    - storage: existence and writability of DOCUMENT_STORAGE_ROOT
    - overall: healthy only if all checks pass
    """
    health = {
        "database": {"status": "unknown", "engine": "unknown"},
        "storage": {"status": "unknown", "path_configured": False},
        "overall": "unknown",
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            if result and result[0] == 1:
                health["database"]["status"] = "connected"
                health["database"]["engine"] = "postgresql"
            else:
                health["database"]["status"] = "error"
    except Exception as exc:
        logger.warning("Health check DB failure: %s", exc)
        health["database"]["status"] = "error"

    # Storage check
    from django.conf import settings as django_settings
    storage_root = getattr(django_settings, "DOCUMENT_STORAGE_ROOT", None)
    if storage_root:
        health["storage"]["path_configured"] = True
        if os.path.isdir(storage_root):
            # Check writability by testing os.access
            if os.access(storage_root, os.W_OK):
                health["storage"]["status"] = "available"
            else:
                health["storage"]["status"] = "read_only"
        else:
            health["storage"]["status"] = "missing"
    else:
        health["storage"]["status"] = "not_configured"

    # Overall
    all_ok = (
        health["database"]["status"] == "connected"
        and health["storage"]["status"] == "available"
    )
    health["overall"] = "healthy" if all_ok else "degraded"

    return health
