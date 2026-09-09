"""WSGI config for the ZapSign backend project.

Exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.handlers.wsgi import WSGIHandler
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application: WSGIHandler = get_wsgi_application()
