"""
Django settings for config project.

Сайт публикаций (аналог 999.md). Подробности — в README.md.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    """Небольшой помощник для чтения настроек из переменных окружения."""
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- Безопасность / режим ---------------------------------------------------

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-yh33j65t7khi^uvwfzaq)otr#0=c0-r3lz^)mv!pjkea6kw29#",
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "*").split(",")

CSRF_TRUSTED_ORIGINS = [
    o for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

# Railway автоматически передаёт публичный домен — добавляем его в хосты/CSRF.
_railway_domain = env("RAILWAY_PUBLIC_DOMAIN")
if _railway_domain:
    if _railway_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_railway_domain)
    origin = f"https://{_railway_domain}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)


# --- Приложения -------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Наши приложения
    "accounts",
    "listings",
    "messaging",
    "panel",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Отдача статики в продакшене (CSS/JS) без отдельного веб-сервера.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Отметка «был онлайн» + IP последнего визита
    "accounts.middleware.LastSeenMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "core.context_processors.site_globals",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- База данных ------------------------------------------------------------
# По умолчанию SQLite (локально). Если задан DATABASE_URL (например, на Railway
# с подключённым PostgreSQL) — используем его, чтобы данные сохранялись.

import dj_database_url  # noqa: E402

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# --- Пользователь / аутентификация -----------------------------------------

AUTH_USER_MODEL = "accounts.User"

# Правила пароля задаём вручную в формах (6–15 символов, без кириллицы),
# поэтому стандартные валидаторы отключаем, чтобы они не мешали ТЗ.
AUTH_PASSWORD_VALIDATORS = []

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

# Ссылка восстановления пароля действительна 1 час (по ТЗ).
PASSWORD_RESET_TIMEOUT = 60 * 60


# --- Интернационализация ----------------------------------------------------

LANGUAGE_CODE = "ru"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Europe/Moscow")
USE_I18N = True
USE_TZ = True


# --- Статика и медиа --------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT", BASE_DIR / "media")

# В продакшене статику отдаёт WhiteNoise (со сжатием и хешированием имён).
# В режиме отладки — стандартное хранилище, чтобы не требовался collectstatic.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Почта ------------------------------------------------------------------
# По умолчанию письма выводятся в консоль (для разработки).
# Для боевого режима задайте SMTP-переменные окружения (см. README).

if env("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = int(env("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
    EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@example.com")


# --- Параметры сайта (по ТЗ) ------------------------------------------------

# Название сайта (логотип клиент ещё не определил).
SITE_NAME = env("SITE_NAME", "Публикации")

# Пользователь считается «онлайн», если был активен в последние N секунд.
ONLINE_TIMEOUT_SECONDS = 60 * 5

# Ограничения для загрузок (по ТЗ).
PHOTO_MIN_SIZE = 30 * 1024          # 30 Кбайт
PHOTO_MAX_SIZE = 3 * 1024 * 1024    # 3 Мб
AVATAR_MIN_SIZE = 30 * 1024
AVATAR_MAX_SIZE = 3 * 1024 * 1024

LISTING_MIN_PHOTOS = 1
LISTING_MAX_PHOTOS = 15

# Разрешаем большие multipart-загрузки (до 15 фото по 3 Мб).
DATA_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000
