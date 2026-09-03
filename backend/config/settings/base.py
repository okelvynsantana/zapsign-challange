"""Shared Django settings.

NOTE: T012 expands this file — it owns the final `INSTALLED_APPS` (DRF, simplejwt,
`rest_framework_api_key`, the six local apps), the `REST_FRAMEWORK` block, the
PostgreSQL `DATABASES` configuration, logging, middleware and auth wiring. What lives
here today is the minimal, import-clean skeleton needed for `manage.py check` to pass.
"""

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

# T012 adds the third-party apps (rest_framework, rest_framework_simplejwt,
# rest_framework_api_key, corsheaders, drf_spectacular) and the six local apps
# (apps.core, apps.companies, apps.documents, apps.signers, apps.integrations,
# apps.automation) here.
THIRD_PARTY_APPS: list[str] = []
LOCAL_APPS: list[str] = []

INSTALLED_APPS: list[str] = [*DJANGO_APPS, *THIRD_PARTY_APPS, *LOCAL_APPS]

# T012/T015 register the structured-logging middleware here.
MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
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
# Stub: PostgreSQL when POSTGRES_DB is provided (docker compose / k8s), SQLite otherwise so
# the project stays runnable without a database server. T012 finalises this.
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
