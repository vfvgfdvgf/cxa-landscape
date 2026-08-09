import os
from pathlib import Path
import logging
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    import dj_database_url
except Exception:
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent

if load_dotenv:
    load_dotenv(BASE_DIR / ".env", override=False)


# ======================
# Helpers
# ======================
def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    raw_value = os.environ.get(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def env_list_any(names, default=""):
    for name in names:
        raw_value = os.environ.get(name)
        if raw_value:
            return [item.strip() for item in raw_value.split(",") if item.strip()]
    return [item.strip() for item in default.split(",") if item.strip()]


def env_int(name, default=0):
    try:
        return int(str(os.environ.get(name, default)).strip())
    except (TypeError, ValueError):
        return int(default)


# ======================
# Core
# ======================
DEFAULT_DEV_SECRET_KEY = "local-dev-only-change-me"
DEBUG = env_bool("DEBUG", False) or env_bool("DJANGO_DEBUG", False)
DJANGO_PRODUCTION = env_bool("DJANGO_PRODUCTION", False)
REQUIRE_PRODUCTION_SERVICES = env_bool("DJANGO_REQUIRE_EXTERNAL_SERVICES", DJANGO_PRODUCTION)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DJANGO_PRODUCTION or not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set outside local DEBUG development.")
    SECRET_KEY = DEFAULT_DEV_SECRET_KEY
if (DJANGO_PRODUCTION or not DEBUG) and SECRET_KEY == DEFAULT_DEV_SECRET_KEY:
    raise ImproperlyConfigured("The development SECRET_KEY cannot be used in production.")


# ======================
# Domain
# ======================
SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "getsiaq.online")
WWW_SITE_DOMAIN = os.environ.get("WWW_SITE_DOMAIN", f"www.{SITE_DOMAIN}")
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
SITE_URL = os.environ.get("SITE_URL", f"https://{SITE_DOMAIN}").rstrip("/")


# ======================
# Hosts
# ======================
ALLOWED_HOSTS = env_list_any(
    ("DJANGO_ALLOWED_HOSTS", "ALLOWED_HOSTS"),
    f"nakheel-najd.onrender.com,{SITE_DOMAIN},{WWW_SITE_DOMAIN},127.0.0.1,localhost,testserver",
)
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = env_list_any(
    ("DJANGO_CSRF_TRUSTED_ORIGINS", "CSRF_TRUSTED_ORIGINS"),
    f"https://{SITE_DOMAIN},https://{WWW_SITE_DOMAIN},https://nakheel-najd.onrender.com",
)
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


# ======================
# Apps
# ======================
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",

    "cloudinary",
    "cloudinary_storage",

    "core.apps.CoreConfig",
]

JAZZMIN_SETTINGS = {
    "site_title": "إدارة نخيل نجد",
    "site_header": "لوحة تحكم نخيل نجد",
    "site_brand": "نخيل نجد",
    "welcome_sign": "إدارة نخيل نجد والمحتوى المحلي",
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_models": [
        "auth.User",
        "auth.Group",
        "core.AIContentGenerationLog",
        "core.BlogComment",
        "core.MediaFolder",
    ],
    "order_with_respect_to": [
        "core.SiteSettings",
        "core.SiteVerification",
        "core.NavigationItem",
        "core.SEOReportIssue",
        "core.SEOAutomationRun",
        "core.SearchConsoleQuery",
        "core.LegacyRedirect",
        "core.City",
        "core.District",
        "core.Service",
        "core.ServiceCategory",
        "core.ServiceTag",
        "core.CityServicePage",
        "core.Page",
        "core.BlogPost",
        "core.BlogCategory",
        "core.BlogTag",
        "core.Project",
        "core.Lead",
        "core.Testimonial",
        "core.PageMedia",
        "core.LibraryImage",
    ],
    "custom_links": {
        "core": [
            {
                "name": "مولد المحتوى بالذكاء الاصطناعي",
                "url": "/admin/ai-content/",
                "icon": "fas fa-robot",
            },
        ]
    },
    "icons": {
        "core.SiteSettings": "fas fa-cogs",
        "core.SiteVerification": "fas fa-shield-alt",
        "core.NavigationItem": "fas fa-list",
        "core.SEOReportIssue": "fas fa-chart-line",
        "core.SEOAutomationRun": "fas fa-sync-alt",
        "core.SearchConsoleQuery": "fas fa-search",
        "core.LegacyRedirect": "fas fa-route",
        "core.City": "fas fa-map-marker-alt",
        "core.District": "fas fa-map-signs",
        "core.Service": "fas fa-tools",
        "core.ServiceCategory": "fas fa-layer-group",
        "core.ServiceTag": "fas fa-tag",
        "core.CityServicePage": "fas fa-link",
        "core.Page": "fas fa-file-alt",
        "core.BlogPost": "fas fa-newspaper",
        "core.BlogCategory": "fas fa-folder-open",
        "core.BlogTag": "fas fa-tags",
        "core.Project": "fas fa-briefcase",
        "core.Lead": "fas fa-phone",
        "core.Testimonial": "fas fa-star",
        "core.PageMedia": "fas fa-image",
        "core.LibraryImage": "fas fa-images",
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "default_theme_mode": "auto",
    "navbar": "navbar-white navbar-light",
    "sidebar": "sidebar-dark-primary",
    "accent": "accent-success",
    "rtl": True,
}


# ======================
# Middleware
# ======================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.RequestIdMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "core.middleware.LegacyRedirectMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ======================
# URLs
# ======================
ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_defaults",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"


# ======================
# Headless API
# ======================
FRONTEND_URL = os.environ.get("FRONTEND_URL", f"https://{SITE_DOMAIN}").rstrip("/")
FRONTEND_API_SECRET = os.environ.get("FRONTEND_API_SECRET", "").strip()
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    f"https://{SITE_DOMAIN},https://{WWW_SITE_DOMAIN}",
)
if DEBUG:
    for development_origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        if development_origin not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(development_origin)
        if development_origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(development_origin)

from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (*default_headers, "x-frontend-secret")
CORS_EXPOSE_HEADERS = ("X-Request-ID",)
CORS_ALLOW_CREDENTIALS = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    # Unsupported writes return 405, while any implemented write is denied unless
    # its view opts in explicitly (submission views require the frontend secret).
    "DEFAULT_PERMISSION_CLASSES": ["core.api.permissions.PublicReadOnlyPermission"],
    "DEFAULT_PAGINATION_CLASS": "core.api.pagination.PublicPageNumberPagination",
    "PAGE_SIZE": env_int("API_PAGE_SIZE", 12),
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "core.api.utils.public_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"submissions": os.environ.get("API_SUBMISSION_RATE", "10/hour")},
}


# ======================
# Database
# ======================
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    if dj_database_url is None:
        raise ImproperlyConfigured(
            "DATABASE_URL is set, but dj-database-url is not installed. "
            "Run `pip install -r requirements.txt`."
        )
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=not DEBUG,
        )
    }
else:
    if REQUIRE_PRODUCTION_SERVICES:
        raise ImproperlyConfigured("DATABASE_URL is required when DJANGO_REQUIRE_EXTERNAL_SERVICES is enabled.")
    # Local fallback: keep development simple when DATABASE_URL is not provided.
    SQLITE_NAME = os.environ.get("SQLITE_NAME", "db.sqlite3").strip() or "db.sqlite3"
    SQLITE_PATH = Path(SQLITE_NAME)
    if not SQLITE_PATH.is_absolute():
        SQLITE_PATH = BASE_DIR / SQLITE_PATH

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_PATH,
        }
    }


# ======================
# Static
# ======================
STATIC_URL = "/static/"
STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", "staticfiles_build"))
if not STATIC_ROOT.is_absolute():
    STATIC_ROOT = BASE_DIR / STATIC_ROOT
STATICFILES_DIRS = [
    path for path in (BASE_DIR / "static", BASE_DIR / "imge") if path.exists()
]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
if not MEDIA_ROOT.is_absolute():
    MEDIA_ROOT = BASE_DIR / MEDIA_ROOT
DJANGO_SERVE_MEDIA_FILES = env_bool("DJANGO_SERVE_MEDIA_FILES", DEBUG)


# ======================
# 🔥 STORAGE (FIX النهائي)
# ======================
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
USE_CLOUDINARY_MEDIA = env_bool("USE_CLOUDINARY_MEDIA", False)
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "").strip()
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "").strip()
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "").strip()


def cloudinary_credentials():
    """Resolve Cloudinary credentials from either CLOUDINARY_URL or split env vars.

    django-cloudinary-storage supports both forms, but validating and normalizing the
    values here prevents an incomplete Render secret from surviving until the first
    admin upload and failing with a 500 ("Must supply api_secret").
    """
    cloud_name = CLOUDINARY_CLOUD_NAME
    api_key = CLOUDINARY_API_KEY
    api_secret = CLOUDINARY_API_SECRET

    if CLOUDINARY_URL:
        parsed = urlsplit(CLOUDINARY_URL)
        if parsed.scheme != "cloudinary":
            raise ImproperlyConfigured(
                "CLOUDINARY_URL must use cloudinary://api_key:api_secret@cloud_name."
            )
        cloud_name = cloud_name or (parsed.hostname or "")
        api_key = api_key or unquote(parsed.username or "")
        api_secret = api_secret or unquote(parsed.password or "")

    return cloud_name.strip(), api_key.strip(), api_secret.strip()


CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET = cloudinary_credentials()
if REQUIRE_PRODUCTION_SERVICES and not USE_CLOUDINARY_MEDIA:
    raise ImproperlyConfigured("USE_CLOUDINARY_MEDIA must be enabled for production media storage.")
if USE_CLOUDINARY_MEDIA:
    missing_cloudinary = [
        label
        for label, value in (
            ("cloud name", CLOUDINARY_CLOUD_NAME),
            ("API key", CLOUDINARY_API_KEY),
            ("API secret", CLOUDINARY_API_SECRET),
        )
        if not value
    ]
    if missing_cloudinary:
        raise ImproperlyConfigured(
            "Cloudinary media storage is enabled but credentials are incomplete: "
            + ", ".join(missing_cloudinary)
            + ". Set CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name "
            "or CLOUDINARY_CLOUD_NAME/CLOUDINARY_API_KEY/CLOUDINARY_API_SECRET."
        )

    # Explicit settings take precedence over environment autodetection in
    # django-cloudinary-storage and make the configuration deterministic on Render.
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY": CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
        "SECURE": True,
    }

    # Configure the underlying Cloudinary SDK as well.  This is intentionally done
    # before the storage backend is first instantiated.
    import cloudinary

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
    STORAGES["default"]["BACKEND"] = "cloudinary_storage.storage.MediaCloudinaryStorage"

WHITENOISE_MANIFEST_STRICT = env_bool("WHITENOISE_MANIFEST_STRICT", False)
WHITENOISE_MAX_AGE = env_int("WHITENOISE_MAX_AGE", 86400)


# ======================
# Auth
# ======================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ======================
# Security
# ======================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nakheel-najd-cache",
    }
}

# Bound request bodies before Django reads them into memory.
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 8 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)
DATA_UPLOAD_MAX_NUMBER_FILES = env_int("DATA_UPLOAD_MAX_NUMBER_FILES", 30)


USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ENABLE_HTTPS_SECURITY = (not DEBUG) and env_bool(
    "DJANGO_ENABLE_HTTPS_SECURITY",
    DJANGO_PRODUCTION or bool(RENDER_EXTERNAL_HOSTNAME),
)

if ENABLE_HTTPS_SECURITY:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", True)
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"


# ======================
# Logging
# ======================
LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
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
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "gunicorn.error": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "core": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}

if ENABLE_HTTPS_SECURITY:
    logging.captureWarnings(True)
