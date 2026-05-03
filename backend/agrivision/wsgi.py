"""WSGI config for AgriVision."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agrivision.settings")

application = get_wsgi_application()
