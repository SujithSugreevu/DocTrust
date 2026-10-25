"""
WSGI config for DocTrust project.
"""
import os
from doctrust.startup import log_startup_failure

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctrust.settings")

try:
    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()
except Exception as exc:
    log_startup_failure("WSGI", exc)
    raise
