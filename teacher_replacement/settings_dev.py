from .settings_base import *  # noqa: F401,F403
import os


DEBUG = True
ALLOWED_HOSTS = [item.strip() for item in str(os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")).split(",") if item.strip()]
CORS_ALLOW_ALL_ORIGINS = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
