import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .cors import desde_entorno

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-cambiar-en-produccion")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h]

# Render define RENDER_EXTERNAL_HOSTNAME en los servicios web: se habilita solo ese dominio.
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS = [f"https://{_render_host}"]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Módulos funcionales del sistema. Para sumar uno nuevo (p. ej. "alumnos") basta con crear
# apps/<nombre>/ y agregarlo acá: ver apps/core/modulos.py para el contrato.
MODULOS = ["academico", "horarios", "rrhh", "consulta_docente"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "apps.core",
    *[f"apps.{m}" for m in MODULOS],
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

def _base_de_datos():
    """Lee DATABASE_URL tolerando espacios y comillas de más (errores comunes al pegarla en Render) y,
    si no se puede interpretar, falla diciendo qué mirar sin mostrar la contraseña."""
    url = os.environ.get("DATABASE_URL", "").strip().strip("\"'").strip()
    try:
        return dj_database_url.parse(url, conn_max_age=600) if url else dj_database_url.parse(
            f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600
        )
    except dj_database_url.ParseError as error:
        esquema = url.split("://")[0] if "://" in url else "(sin «://»)"
        raise ImproperlyConfigured(
            f"DATABASE_URL no es una URL válida (empieza con {esquema!r}, tiene {len(url)} caracteres). "
            "Debe ser postgresql://usuario:clave@host:puerto/base; si la clave tiene @ / : # o % hay que "
            "codificarlos (@ = %40, / = %2F, : = %3A, # = %23, % = %25)."
        ) from error


DATABASES = {"default": _base_de_datos()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["apps.core.permissions.LecturaAutenticadaEscrituraAdmin"],
    "EXCEPTION_HANDLER": "apps.core.exceptions.manejador_excepciones",
    "DEFAULT_PAGINATION_CLASS": None,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

CORS_ALLOWED_ORIGINS, _cors_regex = desde_entorno()
CORS_ALLOWED_ORIGIN_REGEXES = [_cors_regex] if _cors_regex else []
