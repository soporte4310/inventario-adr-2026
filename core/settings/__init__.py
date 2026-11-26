"""
Elige la configuración según ENTORNO y, si no está definido, según DEBUG.

Orden de prioridad:
  1. ENTORNO=staging  -> staging.py    (Cloudinary, Clever Cloud y Mailtrap)
  2. DEBUG=True       -> local.py      (desarrollo con MySQL y Mailtrap)
  3. cualquier otro   -> production.py (Render, Cloudinary y SendGrid)
"""

from decouple import config

if config('ENTORNO', default='').strip().lower() == 'staging':
    from .staging import *
elif config('DEBUG', default=True, cast=bool):
    from .local import *
else:
    from .production import *
