"""
ASGI config for DocTrust project.
"""
import os
from doctrust.startup import log_startup_failure

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctrust.settings")

try:
    from django.core.asgi import get_asgi_application

    application = get_asgi_application()
except Exception as exc:
    log_startup_failure("ASGI", exc)
    raise
