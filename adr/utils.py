# profiles/utils.py
from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from adr.models import Categoria, Marca, Catalogo, Activo
import pandas as pd


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

def enviar_notificacion_asunto(
    asunto: str,
    mensaje: str,
    destinatarios: list[str],
    from_email: str | None = None,
    html_content: str | None = None,
):
    """
    Envía un correo usando SendGrid HTTP API en segundo plano.
    No bloquea la operación principal y evita timeouts de Gunicorn.

    Args:
        asunto: Asunto del correo
        mensaje: Texto plano (fallback si el cliente no soporta HTML)
        destinatarios: Lista de emails
        from_email: Remitente (opcional, usa EMAIL_FROM por defecto)
        html_content: HTML del correo (opcional, si se pasa se envía como HTML)
    """
    import logging
    import threading
    from decouple import config
    
    logger = logging.getLogger(__name__)

    # Auto-generar HTML si no se proporcionó explícitamente
    if html_content is None:
        try:
            from adr.email_template import auto_html_from_plain_text
            html_content = auto_html_from_plain_text(asunto, mensaje)
        except Exception:
            pass  # Si falla, se enviará solo texto plano
    
    def _enviar_en_background():
        """Función interna que ejecuta el envío en un hilo separado usando SendGrid API"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, To
            
            # Obtener configuración
            api_key = config('SENDGRID_API_KEY', default='')
            sender_email = from_email or config('EMAIL_FROM', default='iquiquepracticantes@gmail.com')
            
            if not api_key:
                logger.error("❌ SENDGRID_API_KEY no está configurada")
                return
            
            # Crear el mensaje
            message = Mail(
                from_email=sender_email,
                to_emails=[To(email) for email in destinatarios],
                subject=asunto,
                plain_text_content=mensaje,
                html_content=html_content,
            )
            
            # Enviar usando la API HTTP
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ Correo enviado exitosamente: '{asunto}' a {destinatarios}")
            else:
                logger.error(f"❌ Error SendGrid (código {response.status_code}): {response.body}")
                
        except Exception as e:
            logger.error(f"❌ Error al enviar correo '{asunto}' a {destinatarios}: {e}")
    
    # Iniciar el hilo para enviar el correo sin bloquear
    thread = threading.Thread(target=_enviar_en_background, daemon=True)
    thread.start()
    logger.info(f"📧 Correo programado para envío en segundo plano: '{asunto}'")



def fusionar_categorias(nombre_correcto, nombre_incorrecto):
    """Mueve todos los catálogos de una categoría mala a la buena y elimina la mala."""
    try:
        with transaction.atomic():
            cat_correcta = Categoria.objects.get(nombre__iexact=nombre_correcto)
            cat_mala = Categoria.objects.get(nombre__iexact=nombre_incorrecto)
            
            # Buscamos todos los catálogos que usan la categoría mala
            catalogos = Catalogo.objects.filter(categoria=cat_mala)
            cantidad = catalogos.count()
            
            # Reasignamos masivamente
            catalogos.update(categoria=cat_correcta)
            
            # Ahora que no tiene catálogos dependientes, la podemos borrar
            cat_mala.delete()
            print(f"Éxito: {cantidad} catálogos movidos de '{nombre_incorrecto}' a '{nombre_correcto}'. Categoría eliminada.")
    except Exception as e:
        print(f"Error: {e}")


def fusionar_marcas(nombre_correcto, nombre_incorrecto):
    """Mueve todos los catálogos de una marca mal escrita a la correcta y la elimina."""
    try:
        with transaction.atomic():
            marca_correcta = Marca.objects.get(nombre__iexact=nombre_correcto)
            marca_mala = Marca.objects.get(nombre__iexact=nombre_incorrecto)
            
            catalogos = Catalogo.objects.filter(marca=marca_mala)
            cantidad = catalogos.count()
            
            catalogos.update(marca=marca_correcta)
            marca_mala.delete()
            print(f"Éxito: {cantidad} catálogos movidos de '{nombre_incorrecto}' a '{nombre_correcto}'. Marca eliminada.")
    except Exception as e:
        print(f"Error: {e}")


def _get_excel_val(row, column_name, default=None, to_upper=False):
    """
    Función auxiliar para extraer valores de Pandas de forma segura.
    Evita que las celdas vacías de Excel se conviertan en el string "None".
    """
    val = row.get(column_name)
    if pd.isna(val) or val is None:
        return default
    
    val_str = str(val).strip()
    if val_str.upper() in ['NONE', 'NAN', 'NULL', '']:
        return default
        
    return val_str.upper() if to_upper else val_str