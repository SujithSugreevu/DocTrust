"""Safe diagnostics for Django application startup and health failures."""

import logging
import os
import re
import traceback


_URL_CREDENTIALS_RE = re.compile(r"(?i)(://[^/\s:@]+:)[^@\s/]+(@)")
_SENSITIVE_VALUE_RE = re.compile(
    r"(?i)\b(password|secret|token|authorization|cookie|api[_-]?key)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_SENSITIVE_ENV_NAMES = (
    "DJANGO_SECRET_KEY",
    "DATABASE_URL",
    "DATABASE_URL_UNPOOLED",
    "POSTGRES_PASSWORD",
    "DJANGO_EMAIL_HOST_PASSWORD",
    "VERCEL_OIDC_TOKEN",
)


def format_safe_exception(exc: BaseException) -> str:
    """Return a traceback with known credential-bearing values redacted."""
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    for env_name in _SENSITIVE_ENV_NAMES:
        value = os.environ.get(env_name)
        if value:
            trace = trace.replace(value, "<redacted>")

    trace = _URL_CREDENTIALS_RE.sub(r"\1<redacted>\2", trace)
    return _SENSITIVE_VALUE_RE.sub(r"\1\2<redacted>", trace)


def log_startup_failure(interface: str, exc: BaseException) -> None:
    """Log a useful, redacted startup traceback before re-raising the error."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.ERROR)

    logging.getLogger("doctrust.startup").error(
        "Django %s application initialization failed:\n%s",
        interface,
        format_safe_exception(exc),
    )
