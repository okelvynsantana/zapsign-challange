"""Shared Django settings — every value is environment-driven via `config.settings.env`.

Persistence is PostgreSQL (Constitution Principle VI). A SQLite fallback is kept for the
case where `POSTGRES_DB` is unset, so the suite and `manage.py check` run on a bare clone
without a database server; the Compose stack, the Kubernetes manifests and CI all set
`POSTGRES_DB` and therefore always exercise PostgreSQL.
"""

from datetime import timedelta
from pathlib import Path
from typing import Any

from config.settings.env import env_bool, env_int, env_list, env_str

# backend/config/settings/base.py -> backend/
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# --------------------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------------------
SECRET_KEY: str = env_str("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")

DEBUG: bool = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS: list[str] = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

# --------------------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------------------
DJANGO_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS: list[str] = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_api_key",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS: list[str] = [
    "apps.core",
    "apps.companies",
    "apps.documents",
    "apps.signers",
    "apps.integrations",
    "apps.automation",
]

INSTALLED_APPS: list[str] = [*DJANGO_APPS, *THIRD_PARTY_APPS, *LOCAL_APPS]

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.RequestTimingLogger",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF: str = "config.urls"

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION: str = "config.wsgi.application"
ASGI_APPLICATION: str = "config.asgi.application"

# --------------------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------------------
_POSTGRES_DB: str = env_str("POSTGRES_DB", "")

if _POSTGRES_DB:
    DATABASES: dict[str, dict[str, Any]] = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _POSTGRES_DB,
            "USER": env_str("POSTGRES_USER", "postgres"),
            "PASSWORD": env_str("POSTGRES_PASSWORD", ""),
            "HOST": env_str("POSTGRES_HOST", "localhost"),
            "PORT": env_str("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 60),
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        },
    }

# --------------------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS: list[dict[str, Any]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------------------
REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT: dict[str, Any] = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 7)),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS: dict[str, Any] = {
    "TITLE": "Document & Signature Management System API",
    "DESCRIPTION": "Documents, signers, ZapSign submission, AI analysis and reports.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
}

# --------------------------------------------------------------------------------------
# CORS (the SPA is served from a different origin in development)
# --------------------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    ["http://localhost:4200", "http://127.0.0.1:4200"],
)

# --------------------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------------------
LANGUAGE_CODE: str = "en-us"
TIME_ZONE: str = "UTC"
USE_I18N: bool = True
USE_TZ: bool = True

# --------------------------------------------------------------------------------------
# Static files
# --------------------------------------------------------------------------------------
STATIC_URL: str = "static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------------------
# Alerts (bonus — User Story 5)
# --------------------------------------------------------------------------------------
#: A document pending signature for longer than this is surfaced as a stalled alert.
ALERT_STALLED_DAYS: int = env_int("ALERT_STALLED_DAYS", 5)

# --------------------------------------------------------------------------------------
# Structured logging (Constitution Principle V, FR-029)
# --------------------------------------------------------------------------------------
LOG_LEVEL: str = env_str("DJANGO_LOG_LEVEL", "INFO")

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation_id": {"()": "apps.core.logging.CorrelationIdFilter"},
    },
    "formatters": {
        "json": {
            "()": "apps.core.logging.JsonFormatter",
            "format": "%(timestamp)s %(level)s %(logger)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["correlation_id"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "api.request": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "api.health": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "integrations.gateway": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
