# profiles/utils.py
from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMessage
import logging
import threading


def make_avatar_square(django_file, size=512, fmt="WEBP", quality=86):
    """
    - Corrige orientación EXIF
    - Recorte centrado a cuadrado
    - Redimensiona con LANCZOS
    - Exporta a WEBP (o JPEG)
    """
    img = Image.open(django_file)
    img = ImageOps.exif_transpose(img)     # corrige orientación
    img = img.convert("RGB")

    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top  = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size), Image.LANCZOS)

    buf = BytesIO()
    if fmt.upper() == "WEBP":
        img.save(buf, "WEBP", quality=quality, method=6)
        ext = "webp"
    else:
        img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        ext = "jpg"

    name = f"avatar_{uuid4().hex}.{ext}"
    return ContentFile(buf.getvalue(), name=name)


logger = logging.getLogger(__name__)

def enviar_notificacion_asunto(asunto, mensaje, destinatarios, html_content=None):
    """
    Envía una notificación por correo de forma asíncrona.
    Utiliza el backend configurado en settings.py automáticamente.
    """
    if not destinatarios:
        logger.warning("Intentando enviar correo sin destinatarios.")
        return

    # Validar que los destinatarios sean una lista
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]

    def send_email_thread(subject, body, recipients, html):
        try:
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
            )
            
            if html:
                email.content_subtype = "html"
            
            # Django seleccionará automáticamente el backend:
            # (Mailtrap en Local, SendGrid en Producción)
            email.send(fail_silently=False)
            
            logger.info(f"✅ Correo enviado con éxito: '{subject}'")
        except Exception as e:
            logger.error(f"❌ Error crítico al enviar correo: {str(e)}")

    # Iniciar el hilo para no bloquear la respuesta del servidor
    thread = threading.Thread(
        target=send_email_thread, 
        args=(asunto, mensaje, destinatarios, html_content)
    )
    
    logger.info(f"📧 Correo programado para envío en segundo plano: '{asunto}'")
    thread.start()