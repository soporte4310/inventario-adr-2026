"""
Ajustes para producción: MySQL, Cloudinary y SendGrid.
"""
from .base import *

DEBUG = False

# Hosts y Seguridad
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
RENDER_EXTERNAL_HOSTNAME = config('RENDER_EXTERNAL_HOSTNAME', default=None)
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']

# 1. Base de Datos (MySQL - Render)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME').strip(),
        'USER': config('DB_USER').strip(),
        'PASSWORD': config('DB_PASSWORD').strip(),
        'HOST': config('DB_HOST').strip(),
        'PORT': config('DB_PORT', default='3306').strip(),
        'OPTIONS': {'connect_timeout': 10}
    }
}

# 2. Almacenamiento (Cloudinary + WhiteNoise)
import cloudinary
cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME').strip(),
    api_key=config('CLOUDINARY_API_KEY').strip(),
    api_secret=config('CLOUDINARY_API_SECRET').strip(),
    secure=True
)

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        # WhiteNoise es mejor para servir estáticos en Render
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME').strip(),
    'API_KEY': config('CLOUDINARY_API_KEY').strip(),
    'API_SECRET': config('CLOUDINARY_API_SECRET').strip(),
}

# 3. Email (SendGrid HTTP API)
_sendgrid_key = config('SENDGRID_API_KEY', default='')
if _sendgrid_key:
    EMAIL_BACKEND = 'core.sendgrid_backend.SendGridHTTPBackend'
    DEFAULT_FROM_EMAIL = config('EMAIL_FROM', default='soporte4310@gmail.com')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='soporte4310@gmail.com')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Destinatarios del reporte semanal
_email_recipients_env = config('EMAIL_RECIPIENTS', default='')
if _email_recipients_env:
    EMAIL_RECIPIENTS = [email.strip() for email in _email_recipients_env.split(',')]
else:
    EMAIL_RECIPIENTS = ['wtapia@inacap.cl', 'hleris@inacap.cl'] # Fallback institucional

# 4. Logging de Producción
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
        'level': 'WARNING',
    },
}