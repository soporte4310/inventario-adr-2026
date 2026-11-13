import os
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Reglas de validación estricta
validador_solo_letras = RegexValidator(
    regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
    message='Solo se admiten letras y espacios. Sin números ni caracteres especiales.'
)
validador_alfanumerico_nombres = RegexValidator(
    regex=r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-\.]+$',
    message='Solo se admiten letras, números, espacios, guiones y puntos.'
)
validador_codigo_estricto = RegexValidator(
    regex=r'^[a-zA-Z0-9\-]+$',
    message='Solo se admiten letras, números y guiones medios. Sin espacios.'
)
validador_solo_numeros = RegexValidator(
    regex=r'^\d+$',
    message='Este campo debe contener estrictamente números enteros.'
)
validador_telefono = RegexValidator(
    # El "56" (código de país) es opcional COMO GRUPO: antes "56?" solo hacía
    # opcional el "6" y dejaba el "5" obligatorio, rechazando un número local
    # de 9 dígitos sin código de país (ej: 912345678).
    regex=r'^\+?(56)?\d{9}$',
    message='Formato de teléfono no válido. Use solo números y un "+" opcional (Ej: +56912345678).'
)
validador_texto_seguro = RegexValidator(
    regex=r'^[^<>{}]+$', # Previene inyección de etiquetas HTML/JS básicas
    message='El texto contiene caracteres no permitidos (como <, >, {, }).'
)
# Nombres de red/hostname (ej: IQQ_E540_BODEGA): los guiones bajos son parte
# habitual de esa convención, por eso necesita un validador propio en vez de
# reutilizar validador_codigo_estricto (que no los admite).
validador_nombre_red = RegexValidator(
    regex=r'^[a-zA-Z0-9_\-]+$',
    message='Solo se admiten letras, números, guiones y guiones bajos. Sin espacios.'
)
# MAC address: acepta con o sin separadores (los datos reales del proveedor
# vienen sin separadores, ej: 644ED7D71BB2), pero solo caracteres hexadecimales.
validador_mac = RegexValidator(
    regex=r'^[0-9A-Fa-f]{2}([:\-]?[0-9A-Fa-f]{2}){5}$',
    message='Formato de MAC no válido (use solo dígitos hexadecimales, con o sin separadores).'
)

def validar_extension_imagen(imagen):
    """
    Valida que la imagen sea JPEG, JPG, PNG, WEBP o AVIF
    """
    if imagen.format not in ['JPEG', 'JPG', 'PNG', 'WEBP', 'AVIF']:
        raise ValidationError(
            f"Formato de imagen no válido detectado: {imagen.format}. "
            "Por favor sube archivos JPG, PNG, WEBP o AVIF."
        )



FORMATOS_VIDEO_PERMITIDOS = ['.mp4', '.mov', '.webm']
MIME_TYPES_VIDEO_PERMITIDOS = ['video/mp4', 'video/quicktime', 'video/webm']
MAX_VIDEO_SIZE_MB = 100

def validar_archivo_video(archivo):
    """
    Valida extensión, peso y los bytes de cabecera (magic numbers) del archivo.
    No requiere librerías binarias externas (como python-magic).
    """
    if not archivo:
        return

    # 1. Extensión
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in FORMATOS_VIDEO_PERMITIDOS:
        raise ValidationError(
            f"Formato no permitido ({ext}). Solo se admiten: {', '.join(FORMATOS_VIDEO_PERMITIDOS)}."
        )

    # 2. Tamaño máximo
    if archivo.size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f"El video supera el peso máximo permitido de {MAX_VIDEO_SIZE_MB}MB."
        )

    # 3. Tipo MIME declarado si viene desde el navegador
    content_type = getattr(archivo, 'content_type', None)
    if content_type and content_type not in MIME_TYPES_VIDEO_PERMITIDOS:
        raise ValidationError(
            f"Tipo MIME inválido ({content_type}). Se requiere un video MP4, MOV o WebM."
        )

    # 4. Firma binaria (Magic Bytes)
    posicion_original = archivo.tell()
    try:
        archivo.seek(0)
        cabecera = archivo.read(32)
        archivo.seek(posicion_original)

        # MP4/MOV: contiene la marca 'ftyp' en los primeros 16 bytes
        es_mp4_mov = b'ftyp' in cabecera[:16]
        # WebM: inicia con la firma EBML \x1a\x45\xdf\xa3
        es_webm = cabecera.startswith(b'\x1a\x45\xdf\xa3')

        if not (es_mp4_mov or es_webm):
            raise ValidationError(
                "El archivo no es un flujo de video válido o se encuentra corrupto."
            )
    except Exception as e:
        archivo.seek(posicion_original)
        if isinstance(e, ValidationError):
            raise
        raise ValidationError("Error al verificar la integridad del video.")