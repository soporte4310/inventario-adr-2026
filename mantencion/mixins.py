from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import CicloRevision


class CicloAbiertoRequiredMixin:
    """
    Mixin para proteger cualquier vista de revisión (Salas, Impresoras, Oficinas, Laboratorios).
    Bloquea modificaciones si el CicloRevision padre se encuentra FINALIZADO.
    
    Atributos configurables en la vista:
    - revision_model: Modelo de la revisión hija (ej: RevisionSala, RevisionImpresora).
    - pk_url_kwarg: Nombre del parámetro en URL o GET (por defecto 'pk').
    - permitir_lectura_get: Si es True, permite peticiones GET en modo lectura, pero bloquea POST/PUT/DELETE.
                           Si es False (por defecto), bloquea también el acceso al formulario en GET.
    """
    revision_model = None
    pk_url_kwarg = 'pk'
    permitir_lectura_get = False

    # Mapa de redirección automática según el tipo de ciclo
    TABLERO_REDIRECT_MAP = {
        CicloRevision.TipoCiclo.SALAS: 'mantencion:tablero_salas',
        CicloRevision.TipoCiclo.IMPRESORAS: 'mantencion:tablero_impresoras',
        # Futuro:
        # CicloRevision.TipoCiclo.OFICINAS: 'mantencion:tablero_oficinas',
        # CicloRevision.TipoCiclo.LABORATORIOS: 'mantencion:tablero_laboratorios',
    }

    def get_revision_object(self, request, *args, **kwargs):
        """Obtiene la instancia de la revisión (por URL kwarg o por query param como en Cloudinary)."""
        pk = kwargs.get(self.pk_url_kwarg) or request.GET.get(self.pk_url_kwarg) or request.POST.get(self.pk_url_kwarg)
        queryset = self.revision_model.objects.select_related('ciclo')
        return get_object_or_404(queryset, pk=pk)

    def es_peticion_json(self, request):
        """Detecta si la vista es llamada vía fetch/AJAX (ej. subida de videos o firmas)."""
        accept = request.headers.get('Accept', '')
        x_req = request.headers.get('X-Requested-With', '')
        return 'application/json' in accept or x_req == 'XMLHttpRequest'

    def dispatch(self, request, *args, **kwargs):
        # Cargamos la revisión una sola vez y la dejamos disponible en self.revision
        self.revision = self.get_revision_object(request, *args, **kwargs)
        self.ciclo = self.revision.ciclo

        # Verificamos si el ciclo está cerrado
        ciclo_cerrado = (self.ciclo.estado == CicloRevision.EstadoCiclo.FINALIZADO)

        if ciclo_cerrado:
            # Si se permite GET en modo lectura y la petición es GET, dejamos pasar
            if self.permitir_lectura_get and request.method == 'GET':
                return super().dispatch(request, *args, **kwargs)

            mensaje_bloqueo = (
                f"Operación bloqueada: El ciclo '{self.ciclo.nombre}' ya se encuentra finalizado "
                f"y su historial es de solo lectura."
            )

            # 1. Si es un endpoint JSON / Fetch (Videos, Cloudinary, etc.)
            if self.es_peticion_json(request) or request.path.endswith(('video/', 'cloudinary/', 'asociar-video/')):
                return JsonResponse({'error': mensaje_bloqueo}, status=403)

            # 2. Si es navegación tradicional del técnico/administrador
            messages.error(request, mensaje_bloqueo)
            ruta_tablero = self.TABLERO_REDIRECT_MAP.get(self.ciclo.tipo)
            if ruta_tablero:
                return redirect(ruta_tablero, ciclo_id=self.ciclo.id)
            return redirect('mantencion:lista_revisiones')

        return super().dispatch(request, *args, **kwargs)