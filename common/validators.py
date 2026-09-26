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
    regex=r'^\+?56?\d{9}$',
    message='Formato de teléfono no válido. Use solo números y un "+" opcional (Ej: +56912345678).'
)
validador_texto_seguro = RegexValidator(
    regex=r'^[^<>{}]+$', # Previene inyección de etiquetas HTML/JS básicas
    message='El texto contiene caracteres no permitidos (como <, >, {, }).'
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