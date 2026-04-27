"""
Este archivo convierte la carpeta settings en un paquete y actúa como selector.
Importa automáticamente la configuración local o de producción según el DEBUG.
"""

from decouple import config

# Detectar entorno mediante la variable DEBUG del archivo .env
if config('DEBUG', default=True, cast=bool):
    from .local import *
else:
    from .production import *