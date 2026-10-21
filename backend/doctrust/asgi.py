"""
ASGI config for DocTrust project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctrust.settings")

application = get_asgi_application()
