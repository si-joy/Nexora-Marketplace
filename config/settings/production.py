from .base import *  # noqa: F403,F401

# Production starts only with externally supplied secret, hosts and database URL.
if SECRET_KEY == "local-development-only-change-me" or "replace" in SECRET_KEY.lower() or len(SECRET_KEY) < 50:  # noqa: F405
    raise RuntimeError("Set a strong SECRET_KEY in production environment")
if not env("DATABASE_URL", default=""):  # noqa: F405
    raise RuntimeError("DATABASE_URL is required in production")
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":  # noqa: F405
    raise RuntimeError("Production requires a PostgreSQL DATABASE_URL")
if not env("ALLOWED_HOSTS", default=""):  # noqa: F405
    raise RuntimeError("ALLOWED_HOSTS is required in production")

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
# Set HSTS only after confirming every domain and subdomain uses HTTPS.
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
