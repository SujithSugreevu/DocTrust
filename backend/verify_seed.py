"""Backward-compatible wrapper for the read-only demo-data verifier."""

import os

import django
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctrust.settings")
django.setup()

call_command("verify_demo_data")
