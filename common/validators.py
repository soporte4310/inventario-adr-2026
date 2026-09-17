from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Validador para nombres de personas, áreas y cargos (Solo letras y espacios)
validador_solo_letras = RegexValidator(
    regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
    message='Error: Este campo solo admite letras y espacios. No se permiten números ni caracteres especiales (ej: #, @, !).'
)

# Validador para códigos como BDO, NetBIOS, N° de Serie (Alfanumérico sin espacios)
validador_alfanumerico_estricto = RegexValidator(
    regex=r'^[a-zA-Z0-9\-]+$',
    message='Error: Este campo solo admite letras, números y guiones medios. No ingrese espacios ni caracteres especiales.'
)

def validar_extension_imagen(imagen):
    """
    Valida que la imagen sea JEPG, JPG, PNG o WEBP
    """
    if imagen.format not in ['JPEG', 'JPG', 'PNG', 'WEBP']:
        raise ValidationError(
            f"Formato de imagen no válido detectado: {imagen.format}. "
            "Por favor sube archivos JPG, PNG o WEBP."
        )


def validar_video(archivo):
    """
    Valida un archivo de video subido como evidencia.

    A diferencia de las imágenes, el video NO se recomprime en el servidor
    (el proyecto no tiene ffmpeg instalado), así que esta es la única línea
    de defensa: sólo se acepta MP4 y se limita el peso máximo del archivo.
    """
    # Import local para evitar un import circular con utils.py (que a su vez
    # importa validadores de este mismo archivo).
    from .utils import MAX_VIDEO_SIZE_MB

    nombre = (archivo.name or '').lower()
    if not nombre.endswith('.mp4'):
        raise ValidationError("El video debe estar en formato MP4.")

    max_bytes = MAX_VIDEO_SIZE_MB * 1024 * 1024
    if archivo.size > max_bytes:
        raise ValidationError(
            f"El video pesa demasiado ({archivo.size / (1024 * 1024):.1f} MB). "
            f"El máximo permitido es {MAX_VIDEO_SIZE_MB} MB."
        )