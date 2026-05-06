from django.core.exceptions import ValidationError


def validar_extension_imagen(imagen):
    """
    Valida que la imagen sea JEPG, JPG, PNG o WEBP
    """
    if imagen.format not in ['JPEG', 'JPG', 'PNG', 'WEBP']:
        raise ValidationError(
            f"Formato de imagen no válido detectado: {imagen.format}. "
            "Por favor sube archivos JPG, PNG o WEBP."
        )