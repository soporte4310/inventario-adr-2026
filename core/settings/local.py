"""
Configuración para DESARROLLO LOCAL con MySQL y Mailtrap.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# 1. Base de Datos (MySQL Local)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='inventario_adr'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

# 2. Almacenamiento Local (Carpeta media/)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# 3. Email (Mailtrap)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('MAILTRAP_HOST', default='sandbox.smtp.mailtrap.io')
EMAIL_PORT = config('MAILTRAP_PORT', default=2525, cast=int)
EMAIL_HOST_USER = config('MAILTRAP_USER')
EMAIL_HOST_PASSWORD = config('MAILTRAP_PASSWORD')
EMAIL_USE_TLS = True

EMAIL_RECIPIENTS = [
        'jcastillol@inacap.cl',
    ]

# 4. Logging de Desarrollo
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}