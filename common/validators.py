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