"""Procesadores de contexto exclusivos del entorno de staging."""

from staging.email_backend import ultimo_correo as correo_capturado


def ultimo_correo(request):
    """
    Expone el último correo capturado a todas las plantillas.

    Permite que la pantalla de "revisa tu correo" muestre el enlace de
    recuperación en lugar de esperar a que llegue a una bandeja real.
    """
    return {
        'staging_activo': True,
        'staging_ultimo_correo': correo_capturado(),
    }
