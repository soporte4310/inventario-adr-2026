"""
Configuración para STAGING local.

Se activa con ENTORNO=staging y hereda todo de `local.py`; solo reemplaza
los servicios externos que no pueden funcionar dentro de la máquina:

  1. Email  -> backend que captura el correo y muestra el enlace en pantalla.
  2. Logo   -> imagen servida desde static/ en vez de Cloudinary.
  3. Debug  -> barra de depuración apagada para no tapar el contenido.

La base de datos sigue siendo MySQL local (heredado de `local.py`), porque el
script `iniciar_staging.py` se encarga de traer el dump de producción.
"""
import copy
import os

from decouple import config

from .local import *

STAGING_MODE = True

STAGING_DIR = os.path.join(BASE_DIR, 'staging')

# El cliente de pruebas de Django envía el host "testserver", que no está en
# la lista de local.py y provocaría un 400 al probar flujos completos.
ALLOWED_HOSTS = ALLOWED_HOSTS + ['testserver']

# 1. Email: no se envía nada, se captura para mostrarlo en la web.
EMAIL_BACKEND = 'staging.email_backend.StagingEmailBackend'

# 2. Base de datos: el script nunca toca la base del .env, opera sobre una
#    variante con sufijo. Django debe apuntar a esa misma variante o la
#    aplicación arrancaría contra una base vacía. El sufijo tiene que coincidir
#    con SUFIJO_BASE_STAGING de iniciar_staging.py.
SUFIJO_BASE_STAGING = '_staging'
_nombre_configurado = DATABASES['default']['NAME']
if not _nombre_configurado.endswith(SUFIJO_BASE_STAGING):
    DATABASES['default']['NAME'] = f'{_nombre_configurado}{SUFIJO_BASE_STAGING}'

# 3. Plantillas: anteponer la carpeta de staging para que sus overrides
#    ganen sobre las plantillas del proyecto. Se copia la lista original
#    para no mutar el módulo `base.py` que ya fue importado.
TEMPLATES = copy.deepcopy(TEMPLATES)
TEMPLATES[0]['DIRS'] = [os.path.join(STAGING_DIR, 'templates')] + TEMPLATES[0]['DIRS']

_plantillas_opciones = TEMPLATES[0].setdefault('OPTIONS', {})
_procesadores = _plantillas_opciones.setdefault('context_processors', [])
_procesadores.append('staging.context_processors.ultimo_correo')

# 4. El logo de los correos apunta a Cloudinary en producción. En staging
#    se sirve desde static/ para que la imagen también se vea sin depender
#    de un servicio externo.
STAGING_BASE_URL = config('STAGING_BASE_URL', default='http://127.0.0.1:8000').rstrip('/')
EMAIL_LOGO_URL = f'{STAGING_BASE_URL}{STATIC_URL}imagenes/adr_logo_email.png'

# 5. La barra de depuración ocupa media pantalla y no aporta al staging.
DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda request: False}
