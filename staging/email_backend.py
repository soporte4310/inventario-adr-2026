"""
Backend de correo para staging.

Ningún correo sale de la máquina: se guarda en memoria y la pantalla siguiente
lo muestra, de modo que un enlace de recuperación o un código de activación
quede a la vista sin depender de un proveedor externo.

Se guarda una copia en disco bajo `staging/correos/` para poder revisar los
últimos envíos incluso si el servidor se reinicia.
"""
import os
import re
import threading
from datetime import datetime

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

# Correos capturados en este proceso, del más antiguo al más reciente.
BANDEJA = []
LIMITE_BANDEJA = 25

_candado = threading.Lock()

_DIRECTORIO_CORREOS = os.path.join(
    getattr(settings, 'STAGING_DIR', settings.BASE_DIR), 'correos'
)


def ultimo_correo():
    """Devuelve el correo más reciente capturado, o None si no hay ninguno."""
    with _candado:
        if not BANDEJA:
            return None
        return BANDEJA[-1]


def vaciar_bandeja():
    """Olvida los correos capturados. Útil al reiniciar un flujo en pruebas."""
    with _candado:
        BANDEJA.clear()


class StagingEmailBackend(BaseEmailBackend):
    """
    Captura cada mensaje en memoria y en disco sin abrir conexiones de red.

    Reemplaza a SendGrid (producción) y a Mailtrap (local) en el entorno de
    staging, donde no se debe enviar correo real a nadie.
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        enviados = 0
        for mensaje in email_messages:
            cuerpo_html = None
            for contenido, tipo in mensaje.alternatives:
                if tipo == 'text/html':
                    cuerpo_html = contenido
                    break

            registro = {
                'asunto': mensaje.subject,
                'destinatarios': list(mensaje.to or []),
                'remitente': mensaje.from_email or '',
                'cuerpo_texto': mensaje.body or '',
                'cuerpo_html': cuerpo_html,
                'enlaces': _extraer_enlaces(mensaje.body or '', cuerpo_html),
                'fecha': datetime.now(),
            }

            with _candado:
                BANDEJA.append(registro)
                if len(BANDEJA) > LIMITE_BANDEJA:
                    del BANDEJA[0]

            _guardar_en_disco(registro)
            enviados += 1

        return enviados


def _extraer_enlaces(*textos):
    """Junta los enlaces http(s) presentes en los cuerpos del correo."""
    encontrados = []
    for texto in textos:
        if not texto:
            continue
        for enlace in re.findall(r'https?://[^\s"\'<>)]+', texto):
            if enlace not in encontrados:
                encontrados.append(enlace)
    return encontrados


def _guardar_en_disco(registro):
    """Escribe el correo como .html para revisarlo fuera de la aplicación."""
    try:
        os.makedirs(_DIRECTORIO_CORREOS, exist_ok=True)
        marca = registro['fecha'].strftime('%Y%m%d_%H%M%S_%f')
        nombre = f"{marca}.html"
        ruta = os.path.join(_DIRECTORIO_CORREOS, nombre)
        with open(ruta, 'w', encoding='utf-8') as archivo:
            archivo.write(registro['cuerpo_html'] or (
                "<pre>" + registro['cuerpo_texto'] + "</pre>"
            ))
    except OSError:
        # El staging debe seguir funcionando aunque no se pueda escribir en disco.
        pass
