"""
Ajustes comunes que no dependen del entorno.
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

# Aplicaciones organizadas
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]
THIRD_PARTY_APPS = [
    'cloudinary_storage',
    'cloudinary',
    'django_browser_reload',
    'crispy_forms',
    'crispy_tailwind',
    'django_cleanup.apps.CleanupConfig',
    'debug_toolbar',
]
LOCAL_APPS = [
    'adr',
    'usuarios',
    'inventario',
    'accounts.apps.AccountsConfig',
    'core',
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'adr.middleware.CurrentUserMiddleware',
    'accounts.middleware.AccountsCurrentUserMiddleware', 
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "core.context_processors.group_and_user",
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Internacionalización
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Rutas de archivos (Comunes)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Crispy & Tailwind
TAILWIND_APP_NAME = 'theme'
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# Seguridad y Login
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/inventario'
LOGOUT_REDIRECT_URL = '/'
X_FRAME_OPTIONS = "SAMEORIGIN"
LOGIN_FAILED_THRESHOLD = 3
LOGIN_FAILED_WINDOW_SECONDS = 900
LOGIN_LOCK_SECONDS = 60
BACKUP_DIR = config('BACKUP_DIR', default=os.path.join(BASE_DIR, 'backups'))
PASSWORD_RESET_TIMEOUT = 3600

# Para Django Debug Toolbar
INTERNAL_IPS = [
    "127.0.0.1",
]