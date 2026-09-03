"""Production settings."""

from config.settings.base import *
from config.settings.env import env_bool

DEBUG = False

# Behind an ingress/reverse proxy terminating TLS.
SECURE_PROXY_SSL_HEADER: tuple[str, str] = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT: bool = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE: bool = True
CSRF_COOKIE_SECURE: bool = True
