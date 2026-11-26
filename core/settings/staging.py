"""
Configuración para el entorno de staging: Cloudinary, Clever Cloud y Mailtrap.
Se intentó usar SendGrid, pero al usar el 2FA nos banearon la cuenta con el
correo de staging. Se decidió Mailtrap.
"""

from .base import *

# 0. Entorno visible para los devs.
# DEBUG=True no habilita XSS ni CSRF por sí solo: lo que hace es mostrar el
# traceback completo, con rutas, consultas SQL y ajustes. En staging es el 
# precio a pagar para que el error se entienda sin abrir logs. (puede )
DEBUG = True

# 1. Hosts: Render inyecta RENDER_EXTERNAL_HOSTNAME al desplegar.
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

RENDER_EXTERNAL_HOSTNAME = config('RENDER_EXTERNAL_HOSTNAME', default=None)
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [
        f'https://{RENDER_EXTERNAL_HOSTNAME}',
        'https://*.onrender.com',
    ]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')# Render termina el HTTPS en su proxy y nos entrega la conexión como HTTP simple.

# 2. Base de datos (MySQL de Clever Cloud, instancia de staging).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME').strip(),
        'USER': config('DB_USER').strip(),
        'PASSWORD': config('DB_PASSWORD').strip(),
        'HOST': config('DB_HOST').strip(),
        'PORT': config('DB_PORT', default='3306').strip(),
        'OPTIONS': {'connect_timeout': 10},
    }
}

# 3. Almacenamiento (Cloudinary + WhiteNoise)
import cloudinary

cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME').strip(),
    api_key=config('CLOUDINARY_API_KEY').strip(),
    api_secret=config('CLOUDINARY_API_SECRET').strip(),
    secure=True,
)

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        # CompressedStaticFilesStorage no exige el manifiesto que sí pide
        # CompressedManifestStaticFilesStorage: si falta un archivo estático,
        # staging arranca igual en vez de caerse en el build.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME').strip(),
    'API_KEY': config('CLOUDINARY_API_KEY').strip(),
    'API_SECRET': config('CLOUDINARY_API_SECRET').strip(),
}

# 4. Correo (Mailtrap). Captura los mensajes; no llegan a destinatarios reales.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('MAILTRAP_HOST', default='sandbox.smtp.mailtrap.io')
EMAIL_PORT = config('MAILTRAP_PORT', default=2525, cast=int)
EMAIL_HOST_USER = config('MAILTRAP_USER')
EMAIL_HOST_PASSWORD = config('MAILTRAP_PASSWORD')
EMAIL_USE_TLS = True 

DEFAULT_FROM_EMAIL = config('EMAIL_FROM', default='soporte4310staging@gmail.com') #Mail oficial de staging
SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_RECIPIENTS = [DEFAULT_FROM_EMAIL] #Reporte semanal. Para que staging no les escriba por accidente.

# 5. La barra de depuración ocupa media pantalla y, con DEBUG=True, expone
DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda request: False}

# 6. Logging de staging: todo a consola; que es lo que Render muestra.
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
        'level': 'INFO',
    },
}

# Parche de rendimiento 
# Quita apps y middleware de desarrollo: en Render abren conexiones eternas
# y consumen el único worker.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ('django_browser_reload', 'debug_toolbar')]
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m and 'django_browser_reload' not in m]