"""Configurações do ERP para desenvolvimento, homologação e produção."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", True)
ERP_ENVIRONMENT = (
    os.getenv("ERP_ENVIRONMENT", "development" if DEBUG else "production").strip().lower()
)
if ERP_ENVIRONMENT not in {"development", "production"}:
    raise ImproperlyConfigured("ERP_ENVIRONMENT deve ser 'development' ou 'production'.")
if ERP_ENVIRONMENT == "production" and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG deve ser 0 no ambiente de produção.")

version_file = BASE_DIR / "VERSION"
ERP_VERSION = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "dev"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-change-me-before-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY é obrigatória quando DJANGO_DEBUG=0.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "gestao",
    "infraestrutura",
    "helpdesk",
    "cgnat",
    "pagamentos",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.runtime_metadata",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

if os.getenv("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "erp_db"),
            "USER": os.getenv("DB_USER", "erp_admin"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "db"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "OPTIONS": {"connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5"))},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = ["portal.backends.UsernameOrEmailBackend"]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Recife"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "var" / "static"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "core.storage.JazzminCompatibleStaticFilesStorage"
        )
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "var" / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "erp@localhost")

PIX_SIMULATOR_WEBHOOK_TOKEN = os.getenv("PIX_SIMULATOR_WEBHOOK_TOKEN", "")
PIX_ENABLED = env_bool("PIX_ENABLED", DEBUG)
if PIX_ENABLED and not PIX_SIMULATOR_WEBHOOK_TOKEN and DEBUG:
    PIX_SIMULATOR_WEBHOOK_TOKEN = "simulador-local"
elif PIX_ENABLED and not PIX_SIMULATOR_WEBHOOK_TOKEN:
    raise ImproperlyConfigured("PIX_SIMULATOR_WEBHOOK_TOKEN é obrigatório quando DJANGO_DEBUG=0.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}

JAZZMIN_SETTINGS = {
    "site_title": f"Admin - Consultoria ({ERP_ENVIRONMENT})",
    "site_header": (
        "Gestão ERP — Desenvolvimento" if ERP_ENVIRONMENT == "development" else "Gestão ERP"
    ),
    "site_brand": "Painel de Controle",
    "welcome_sign": "Bem-vindo ao ERP de Consultoria",
    "copyright": "Gestão de Provedores e Redes",
    "custom_css": "css/admin_custom.css",
    "custom_js": "js/admin_theme.js",
    "topmenu_links": [
        {
            "name": "Abrir IPAM",
            "url": "ipam:dashboard",
            "permissions": ["infraestrutura.view_subrede"],
        }
    ],
    "custom_links": {
        "infraestrutura": [
            {
                "name": "Abrir painel IPAM",
                "url": "ipam:dashboard",
                "icon": "fas fa-network-wired",
                "permissions": ["infraestrutura.view_subrede"],
            }
        ]
    },
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "gestao.Cliente": "fas fa-building",
        "gestao.Contrato": "fas fa-file-signature",
        "helpdesk.Ticket": "fas fa-ticket-alt",
        "infraestrutura.Equipamento": "fas fa-server",
        "infraestrutura.Vlan": "fas fa-network-wired",
        "infraestrutura.Subrede": "fas fa-project-diagram",
        "infraestrutura.EnderecoIP": "fas fa-ethernet",
        "infraestrutura.GeradorVlanLote": "fas fa-layer-group",
        "infraestrutura.SecaoIPAM": "fas fa-folder-tree",
        "infraestrutura.VRF": "fas fa-route",
        "infraestrutura.HistoricoIPAM": "fas fa-history",
        "portal.PerfilCliente": "fas fa-id-badge",
        "cgnat.CgnatPlan": "fas fa-random",
        "cgnat.CgnatGeneration": "fas fa-file-code",
        "pagamentos.PixCharge": "fas fa-qrcode",
    },
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "default_theme_mode": "auto",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
