"""Local development settings."""

from config.settings.base import *
from config.settings.env import env_list

DEBUG = True

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "0.0.0.0", "backend", "testserver"],
)
