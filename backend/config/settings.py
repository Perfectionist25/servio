import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / '.env')


def _running_in_container() -> bool:
    return Path('/.dockerenv').exists() or os.getenv('RUNNING_IN_DOCKER', '').lower() == 'true'


def _local_service_host(service_name: str, default_port: str, local_default_port: str | None = None) -> tuple[str, str]:
    host = os.getenv(f'{service_name.upper()}_HOST', service_name)
    port = os.getenv(f'{service_name.upper()}_PORT', default_port)

    if not _running_in_container() and host == service_name:
        host = os.getenv(f'{service_name.upper()}_HOST_LOCAL', '127.0.0.1')
        port = os.getenv(f'{service_name.upper()}_PORT_LOCAL', local_default_port or port)

    return host, port


def _local_service_url(env_name: str, service_name: str, default_url: str) -> str:
    raw_url = os.getenv(env_name, default_url)

    if _running_in_container():
        return raw_url

    parsed = urlsplit(raw_url)
    if parsed.hostname != service_name:
        return raw_url

    local_host = os.getenv(f'{service_name.upper()}_HOST_LOCAL', '127.0.0.1')
    local_port = os.getenv(f'{service_name.upper()}_PORT_LOCAL', str(parsed.port or 6379))
    auth_part = ''
    if parsed.username:
        auth_part = parsed.username
        if parsed.password:
            auth_part = f'{auth_part}:{parsed.password}'
        auth_part = f'{auth_part}@'

    netloc = f'{auth_part}{local_host}:{local_port}'
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


POSTGRES_HOST, POSTGRES_PORT = _local_service_host('postgres', '5432', '5433')

SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.tenants',
    'apps.accounts',
    'apps.services',
    'apps.bookings',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'servio'),
        'USER': os.getenv('POSTGRES_USER', 'servio'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'servio'),
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

REDIS_URL = _local_service_url('REDIS_URL', 'redis', 'redis://redis:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'send-booking-reminders-every-minute': {
        'task': 'apps.bookings.tasks.send_booking_reminders',
        'schedule': 60.0,
    },
}

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'servio_uz_bot')
