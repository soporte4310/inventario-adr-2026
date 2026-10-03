import re

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def descarga_forzada(url, nombre=None):
    """
    Convierte una URL de Cloudinary en una que fuerza la descarga del archivo
    (Content-Disposition: attachment) en vez de abrirlo/reproducirlo en el
    navegador. Funciona insertando el flag fl_attachment que entiende
    Cloudinary justo después de '/upload/'. Si se pasa 'nombre', Cloudinary
    además usa ese nombre para el archivo descargado (fl_attachment:nombre).

    En local (FileSystemStorage) la URL no tiene '/upload/', así que esta
    función simplemente la devuelve sin tocar — el enlace sigue funcionando
    normal, solo sin la descarga forzada ni el nombre personalizado.
    """
    if '/upload/' in url:
        flag = f'fl_attachment:{nombre}' if nombre else 'fl_attachment'
        return url.replace('/upload/', f'/upload/{flag}/', 1)
    return url


@register.filter
def nombre_descarga_evidencia(ev):
    """
    Nombre sugerido para descargar una evidencia: ADR_Evidencia_<Tipo>_
    <Ubicación>_<Fecha>, ej: ADR_Evidencia_Impresora_Oficina_Bodega_03-10-2026.
    Sin extensión: Cloudinary le pone la real del archivo.
    """
    revision = ev.revision
    tipo = revision.equipo.get_tipo_display()
    ubicacion = revision.ubicacion_en_revision.nombre if revision.ubicacion_en_revision else 'SinUbicacion'
    ubicacion = re.sub(r'\s+', '_', ubicacion.strip())
    ubicacion = re.sub(r'[^\w\-]', '', ubicacion)
    fecha = timezone.localtime(ev.subido_en).strftime('%d-%m-%Y') if ev.subido_en else ''
    return f"ADR_Evidencia_{tipo}_{ubicacion}_{fecha}"
