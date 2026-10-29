"""
Django settings for DocTrust project.

Environment variables are loaded from the .env file in the project root.
"""

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent  # DocTrust root (where .env lives)

# Load .env from the project root
load_dotenv(PROJECT_ROOT / ".env")

# ── Security ─────────────────────────────────────────────────────────
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")
_INSECURE_DEFAULT_SECRET = "django-insecure-CHANGE-THIS-IN-PRODUCTION"
_configured_secret = os.environ.get("DJANGO_SECRET_KEY", "").strip()
PRODUCTION_CONFIGURATION_ERRORS = []

if DEBUG:
    SECRET_KEY = _configured_secret or _INSECURE_DEFAULT_SECRET
    if os.environ.get("VERCEL"):
        PRODUCTION_CONFIGURATION_ERRORS.append(
            "DJANGO_DEBUG must be False on Vercel."
        )
else:
    SECRET_KEY = _configured_secret or _INSECURE_DEFAULT_SECRET
    if not _configured_secret or _configured_secret == _INSECURE_DEFAULT_SECRET:
        PRODUCTION_CONFIGURATION_ERRORS.append(
            "DJANGO_SECRET_KEY must be set to a non-default value when DJANGO_DEBUG=False."
        )
    elif len(_configured_secret) < 50:
        PRODUCTION_CONFIGURATION_ERRORS.append(
            "DJANGO_SECRET_KEY must be at least 50 characters when DJANGO_DEBUG=False."
        )

FRONTEND_BASE_URL = os.environ.get(
    "FRONTEND_BASE_URL",
    "http://localhost:5173" if DEBUG else "",
).strip().rstrip("/")
if not DEBUG and not FRONTEND_BASE_URL:
    PRODUCTION_CONFIGURATION_ERRORS.append(
        "FRONTEND_BASE_URL must be configured when DJANGO_DEBUG=False."
    )

_allowed_hosts_raw = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
if not _allowed_hosts_raw:
    if DEBUG:
        _allowed_hosts_raw = "localhost,127.0.0.1"
    else:
        PRODUCTION_CONFIGURATION_ERRORS.append(
            "DJANGO_ALLOWED_HOSTS must list the production hostnames when DJANGO_DEBUG=False."
        )
        _allowed_hosts_raw = "localhost,127.0.0.1"

ALLOWED_HOSTS = [
    host.strip()
    for host in _allowed_hosts_raw.split(",")
    if host.strip()
]
if not DEBUG and "*" in ALLOWED_HOSTS:
    PRODUCTION_CONFIGURATION_ERRORS.append(
        "DJANGO_ALLOWED_HOSTS must not contain '*' in production."
    )
if DEBUG and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")


# ── Application definition ───────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # DocTrust apps
    "accounts",
    "documents",
    "auditlog",
    "systemsettings",
]

MIDDLEWARE = [
    "doctrust.middleware.ProductionConfigurationMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "systemsettings.middleware.SessionIdleTimeoutMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "doctrust.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "doctrust.wsgi.application"

# ── Database ─────────────────────────────────────────────────────────
def _database_from_url(url):
    """Convert a Neon PostgreSQL URL into Django's database settings."""
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise ImproperlyConfigured(
            "DATABASE_URL must be a valid PostgreSQL connection URL."
        ) from exc

    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.hostname
        or not parsed.path.strip("/")
    ):
        raise ImproperlyConfigured(
            "DATABASE_URL must include a PostgreSQL scheme, hostname, and database name."
        )

    query = parse_qs(parsed.query)
    options = {}
    if "sslmode" in query:
        options["sslmode"] = query["sslmode"][0]
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": port or 5432,
        "OPTIONS": options,
        # Neon pooled URLs are intended for short-lived web requests.
        "CONN_MAX_AGE": 0,
    }


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or None
DATABASE_URL_UNPOOLED = os.environ.get("DATABASE_URL_UNPOOLED", "").strip() or None
if not DEBUG and not DATABASE_URL:
    PRODUCTION_CONFIGURATION_ERRORS.append(
        "DATABASE_URL must be configured when DJANGO_DEBUG=False."
    )

_use_unpooled_database = os.environ.get(
    "DOCTRUST_USE_UNPOOLED_DATABASE", ""
).strip().lower() in ("true", "1", "yes", "on")
_database_connection_url = (
    DATABASE_URL_UNPOOLED
    if DATABASE_URL_UNPOOLED and _use_unpooled_database
    else DATABASE_URL
)

try:
    _default_database = _database_from_url(_database_connection_url) if _database_connection_url else {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "doctrust_db"),
        "USER": os.environ.get("POSTGRES_USER", "doctrust_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
except ImproperlyConfigured as exc:
    PRODUCTION_CONFIGURATION_ERRORS.append(str(exc))
    _default_database = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "doctrust_db",
        "USER": "doctrust_user",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }

DATABASES = {
    "default": _default_database,
}

# ── Custom user model ────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

# ── Authentication backends ──────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ── Password validation ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalization ─────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static files ─────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Private media / uploaded files ───────────────────────────────────
# Files are stored OUTSIDE the static root and served only through
# authenticated Django views — never directly by the web server.
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))
MEDIA_URL = "/media/"  # Not actually served publicly

# ── Private Document Storage (DocTrust Encapsulated Storage) ──────────
# Storage root is completely separate from source tree, STATIC_ROOT, and MEDIA_ROOT.
DOCUMENT_STORAGE_ROOT = os.environ.get(
    "DOCUMENT_STORAGE_ROOT",
    str(BASE_DIR.parent / "storage" if os.name == "nt" else "/tmp/doctrust/storage"),
)
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_MB * 1024 * 1024
USER_STORAGE_QUOTA_MB = int(os.environ.get("USER_STORAGE_QUOTA_MB", "500"))
USER_STORAGE_QUOTA_BYTES = USER_STORAGE_QUOTA_MB * 1024 * 1024
DELETED_RETENTION_DAYS = int(os.environ.get("DELETED_RETENTION_DAYS", "30"))
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_TEMP_DIR = os.environ.get(
    "FILE_UPLOAD_TEMP_DIR",
    "/tmp/doctrust",
)
try:
    os.makedirs(FILE_UPLOAD_TEMP_DIR, mode=0o700, exist_ok=True)
except OSError as exc:
    raise ImproperlyConfigured(
        "FILE_UPLOAD_TEMP_DIR must be writable by the deployment runtime."
    ) from exc

ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx",
}

# ── Django REST Framework ────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.TabSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "accounts.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [] if ("test" in sys.argv) else [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "100/minute",
        "login": "5/minute",
        "session_verification": "30/minute",
        "password_reset": "5/minute",
        "password_reset_confirm": "5/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ── CORS (for the React dev server) ──────────────────────────────────
_default_dev_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
] if DEBUG else []

_env_cors = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if FRONTEND_BASE_URL:
    _env_cors.append(FRONTEND_BASE_URL)
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(_default_dev_origins + _env_cors))

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (*default_headers, "x-doctrust-session")

# ── CSRF ─────────────────────────────────────────────────────────────
_env_csrf = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if FRONTEND_BASE_URL:
    _env_csrf.append(FRONTEND_BASE_URL)
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_default_dev_origins + _env_csrf))

CSRF_COOKIE_HTTPONLY = False  # React needs to read the CSRF cookie
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_SECURE = not DEBUG

# ── Session ──────────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# ── Default primary key ─────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Email configuration ──────────────────────────────────────────────
# Console backend is used by default in local DEBUG mode for safe development.
# In production, SMTP settings should be provided via environment variables.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL",
    "DocTrust Security <noreply@doctrust.local>",
)

# Password reset token expiration (1 hour = 3600 seconds)
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", "3600"))

# ── Logging ──────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "documents": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "auditlog": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "systemsettings": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
