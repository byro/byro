import os
from contextlib import suppress
from urllib.parse import urlparse

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from pkg_resources import iter_entry_points

from byro.common.settings.config import build_config
from byro.common.settings.utils import log_initial

config, config_files = build_config()
CONFIG = config

##
# This settings file is rather lengthy. It follows this structure:
# Directories, Apps, Url, Security, Databases, Logging, Email, Caching (and Sessions)
# I18n, Auth, Middleware, Templates and Staticfiles, External Apps
#
# Search for "## {AREA} SETTINGS" to navigate this file
##

DEBUG = config.getboolean("site", "debug")

## DIRECTORY SETTINGS
BASE_DIR = config.get("filesystem", "base")
DATA_DIR = config.get(
    "filesystem",
    "data",
    fallback=os.environ.get("BYRO_DATA_DIR", os.path.join(BASE_DIR, "data")),
)
LOG_DIR = config.get("filesystem", "logs", fallback=os.path.join(DATA_DIR, "logs"))
MEDIA_ROOT = config.get("filesystem", "media", fallback=os.path.join(DATA_DIR, "media"))
STATIC_ROOT = config.get(
    "filesystem", "static", fallback=os.path.join(BASE_DIR, "static.dist")
)

for directory in (BASE_DIR, LOG_DIR, STATIC_ROOT, MEDIA_ROOT):
    os.makedirs(directory, exist_ok=True)


## APP SETTINGS
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "compressor",
    "bootstrap4",
    "djangoformsetjs",
    "solo.apps.SoloAppConfig",
    "django_select2",
    "byro.common.apps.CommonConfig",
    "byro.bookkeeping.apps.BookkeepingConfig",
    "byro.documents.apps.DocumentsConfig",
    "byro.mails.apps.MailsConfig",
    "byro.members.apps.MemberConfig",
    "byro.office.apps.OfficeConfig",
    "byro.public.apps.PublicConfig",
    "byro.plugins.profile.ProfilePluginConfig",
    "byro.plugins.sepa.SepaPluginConfig",
    "annoying",
    "django_db_constraints",
]

PLUGINS = []
for entry_point in iter_entry_points(group="byro.plugin", name=None):
    PLUGINS.append(entry_point.module_name)
    INSTALLED_APPS.append(entry_point.module_name)

## URL SETTINGS
SITE_URL = config.get("site", "url", fallback="http://localhost")
INTERNAL_IPS = ["127.0.0.1", "::1", "localhost"]
ALLOWED_HOSTS = [SITE_URL]
if DEBUG:
    ALLOWED_HOSTS += INTERNAL_IPS
ROOT_URLCONF = "byro.urls"
STATIC_URL = "/static/"
MEDIA_URL = "/media/"


## SECURITY SETTINGS
X_FRAME_OPTIONS = "DENY"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_COOKIE_NAME = "byro_csrftoken"
CSRF_TRUSTED_ORIGINS = [urlparse(SITE_URL).hostname]
SESSION_COOKIE_NAME = "byro_session"
SESSION_COOKIE_SECURE = config.getboolean(
    "site", "https", fallback=SITE_URL.startswith("https:")
)
if config.has_option("site", "secret"):
    SECRET_KEY = config.get("site", "secret")
else:
    SECRET_FILE = os.path.join(DATA_DIR, ".secret")
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r") as f:
            SECRET_KEY = f.read().strip()
    else:
        chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        SECRET_KEY = get_random_string(50, chars)
        with open(SECRET_FILE, "w") as f:
            os.chmod(SECRET_FILE, 0o600)
            if hasattr(os, "chown"):
                os.chown(SECRET_FILE, os.getuid(), os.getgid())
            f.write(SECRET_KEY)


## DATABASE SETTINGS
db_name = config.get("database", "name", fallback=os.path.join(DATA_DIR, "db.sqlite3"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_name,
        "USER": config.get("database", "user"),
        "PASSWORD": config.get("database", "password"),
        "HOST": config.get("database", "host"),
        "PORT": config.get("database", "port"),
        "CONN_MAX_AGE": 120,
    }
}
if os.getenv("TRAVIS"):
    DATABASES["default"]["USER"] = "postgres"
    DATABASES["default"]["HOST"] = "localhost"
    DATABASES["default"]["PASSWORD"] = ""

# for docker-compose development
if os.getenv("DEVELOPMENT"):
    DATABASES["default"]["USER"] = "byro"
    DATABASES["default"]["HOST"] = "db"
    DATABASES["default"]["PASSWORD"] = "byro"


## LOGGING SETTINGS
loglevel = "DEBUG" if DEBUG else "INFO"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(levelname)s %(asctime)s %(name)s %(module)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": loglevel,
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "level": loglevel,
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "byro.log"),
            "formatter": "default",
        },
    },
    "loggers": {
        "": {"handlers": ["file", "console"], "level": loglevel, "propagate": True},
        "django.request": {
            "handlers": ["file", "console"],
            "level": loglevel,
            "propagate": True,
        },
        "django.security": {
            "handlers": ["file", "console"],
            "level": loglevel,
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["file", "console"],
            "level": "INFO",  # Do not output all the queries
            "propagate": True,
        },
    },
}

email_level = config.get("logging", "email_level", fallback="ERROR") or "ERROR"
emails = config.get("logging", "email", fallback="").split(",")
MANAGERS = ADMINS = [(email, email) for email in emails if email]
if ADMINS:
    LOGGING["handlers"]["mail_admins"] = {
        "level": email_level,
        "class": "django.utils.log.AdminEmailHandler",
    }


## EMAIL SETTINGS
MAIL_FROM = SERVER_EMAIL = DEFAULT_FROM_EMAIL = config.get("mail", "from")
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_HOST = config.get("mail", "host")
    EMAIL_PORT = config.get("mail", "port")
    EMAIL_HOST_USER = config.get("mail", "user")
    EMAIL_HOST_PASSWORD = config.get("mail", "password")
    EMAIL_USE_TLS = config.getboolean("mail", "tls")
    EMAIL_USE_SSL = config.getboolean("mail", "ssl")


## I18N SETTINGS
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = [("en", _("English")), ("de", _("German"))]
LANGUAGES_NATURAL_NAMES = [("en", "English"), ("de", "Deutsch")]
LOCALE_PATHS = (os.path.join(os.path.dirname(__file__), "locale"),)
FORMAT_MODULE_PATH = ["byro.common.formats"]
TIME_ZONE = config.get("locale", "time_zone")
LANGUAGE_CODE = config.get("locale", "language_code")


## AUTHENTICATION SETTINGS
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


## MIDDLEWARE SETTINGS
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "byro.common.middleware.PermissionMiddleware",
    "byro.common.middleware.SettingsMiddleware",
]


## TEMPLATE AND STATICFILES SETTINGS
template_loaders = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)
if not DEBUG:
    template_loaders = (("django.template.loaders.cached.Loader", template_loaders),)
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "byro.common.context_processors.byro_information",
                "byro.common.context_processors.sidebar_information",
            ],
            "loaders": template_loaders,
        },
    }
]

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)
STATICFILES_DIRS = [os.path.join(BASE_DIR, "byro", "static")]


## EXTERNAL APP SETTINGS
with suppress(ImportError):
    import django_extensions  # noqa

    INSTALLED_APPS.append("django_extensions")

with suppress(ImportError):
    import django_securebox

    INSTALLED_APPS.append("django_securebox")
    MIDDLEWARE.insert(2, "django_securebox.middleware.SecureBoxMiddleware")

with suppress(ImportError):
    import debug_toolbar

    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(2, "debug_toolbar.middleware.DebugToolbarMiddleware")


COMPRESS_ENABLED = COMPRESS_OFFLINE = not DEBUG
COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)
COMPRESS_CSS_FILTERS = (
    # CssAbsoluteFilter is incredibly slow, especially when dealing with our _flags.scss
    # However, we don't need it if we consequently use the static() function in Sass
    # 'compressor.filters.css_default.CssAbsoluteFilter',
    "compressor.filters.cssmin.CSSCompressorFilter",
)
SELECT2_JS = ""
SELECT2_CSS = ""
SELECT2_I18N_PATH = "/static/vendored/select2/js/i18n"

with suppress(ImportError):
    from .local_settings import *

    print(
        "You are using the deprecated local_settings.py – Please move to the byro.cfg format."
    )

WSGI_APPLICATION = "byro.wsgi.application"
log_initial(
    debug=DEBUG,
    config_files=config_files,
    db_name=db_name,
    LOG_DIR=LOG_DIR,
    plugins=PLUGINS,
)
