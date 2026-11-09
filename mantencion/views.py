import os
import json
import time
import cloudinary
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.views.generic import ListView, DetailView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse

from .models import CicloRevision, RevisionSala
from .forms import CerrarRevisionForm, RevisionSalaForm
from inventario.models import Activo

class DashboardInventario(View):
    def get():
        pass




class ListaRevisionesView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CicloRevision
    template_name = 'mantencion/pages/lista_revisiones.html'
    context_object_name = 'revisiones'
    paginate_by = 15
    permission_required = 'mantencion.view_ciclorevision'

    def get_queryset(self):
        # Optimizamos relaciones foráneas y calculamos métricas en una sola query
        queryset = CicloRevision.objects.select_related('creado_por', 'cerrado_por').annotate(
            total_items=Count('revisiones_salas', distinct=True),
            completadas=Count(
                'revisiones_salas',
                filter=~Q(revisiones_salas__estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE),
                distinct=True
            ),
            con_observaciones=Count(
                'revisiones_salas',
                filter=Q(revisiones_salas__estado_general=RevisionSala.EstadoGeneralSala.CON_OBSERVACIONES),
                distinct=True
            ),
            criticas=Count(
                'revisiones_salas',
                filter=Q(revisiones_salas__estado_general=RevisionSala.EstadoGeneralSala.CRITICA),
                distinct=True
            ),
        )

        # 1. Obtener parámetros GET
        search_query = self.request.GET.get('search', '').strip()
        tipo_ciclo = self.request.GET.get('tipo', '').strip()
        estado_ciclo = self.request.GET.get('estado', '').strip()

        # 2. Aplicar filtros dinámicos
        if search_query:
            queryset = queryset.filter(nombre__icontains=search_query)

        if tipo_ciclo:
            queryset = queryset.filter(tipo=tipo_ciclo)

        if estado_ciclo:
            queryset = queryset.filter(estado=estado_ciclo)

        return queryset.order_by('-fecha_inicio', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_lista'] = 'Historial de Revisiones'

        # Mantener valores en el formulario de búsqueda
        search_query = self.request.GET.get('search', '').strip()
        tipo_ciclo = self.request.GET.get('tipo', '').strip()
        estado_ciclo = self.request.GET.get('estado', '').strip()

        context['search_query'] = search_query
        context['tipo_ciclo'] = tipo_ciclo
        context['estado_ciclo'] = estado_ciclo

        # Opciones para los select
        context['tipos'] = self.model.TipoCiclo.choices
        context['estados'] = self.model.EstadoCiclo.choices

        # Query string para mantener filtros al paginar
        query_params = []
        if search_query:
            query_params.append(f'search={search_query}')
        if tipo_ciclo:
            query_params.append(f'tipo={tipo_ciclo}')
        if estado_ciclo:
            query_params.append(f'estado={estado_ciclo}')

        context['query_string'] = '&' + '&'.join(query_params) if query_params else ''

        return context




class CrearRevisionView(View):
    def get():
        pass

class DetalleRevisionView(View):
    def get():
        pass




class CerrarRevisionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Permite exclusivamente al superusuario forzar el cierre de un ciclo preventivo."""

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(
            self.request,
            "Acceso denegado: Solo los administradores / superusuarios pueden forzar el cierre de un ciclo.",
        )
        return redirect("mantencion:lista_revisiones")

    def get(self, request, pk):
        ciclo = get_object_or_404(CicloRevision, pk=pk)

        # Si ya está cerrado, no permitir volver a cerrarlo
        if ciclo.estado == CicloRevision.EstadoCiclo.FINALIZADO:
            messages.warning(
                request, f"El ciclo '{ciclo.nombre}' ya se encuentra cerrado."
            )
            return redirect("mantencion:tablero_salas", ciclo_id=ciclo.id)

        form = CerrarRevisionForm(instance=ciclo)
        context = {
            "ciclo": ciclo,
            "form": form,
            "total_salas": ciclo.total_salas,
            "revisadas": ciclo.total_revisadas,
            "pendientes": ciclo.total_pendientes,
            "porcentaje": ciclo.porcentaje_avance,
            "titulo": f"Cerrar Ciclo: {ciclo.nombre}",
        }
        return render(request, "mantencion/pages/cerrar_revision.html", context)

    def post(self, request, pk):
        ciclo = get_object_or_404(CicloRevision, pk=pk)

        if ciclo.estado == CicloRevision.EstadoCiclo.FINALIZADO:
            messages.warning(request, "Este ciclo ya estaba cerrado.")
            return redirect("mantencion:tablero_salas", ciclo_id=ciclo.id)

        form = CerrarRevisionForm(request.POST, instance=ciclo)
        if form.is_valid():
            ciclo_actualizado = form.save(commit=False)
            ciclo_actualizado.estado = CicloRevision.EstadoCiclo.FINALIZADO
            ciclo_actualizado.cerrado_por = request.user
            ciclo_actualizado.fecha_cierre = timezone.now()
            ciclo_actualizado.save()

            messages.success(
                request,
                f"El ciclo '{ciclo.nombre}' ha sido cerrado exitosamente por {request.user.username}.",
            )
            return redirect("mantencion:lista_revisiones")

        context = {
            "ciclo": ciclo,
            "form": form,
            "total_salas": ciclo.total_salas,
            "revisadas": ciclo.total_revisadas,
            "pendientes": ciclo.total_pendientes,
            "porcentaje": ciclo.porcentaje_avance,
            "titulo": f"Cerrar Ciclo: {ciclo.nombre}",
        }
        return render(request, "mantencion/pages/cerrar_revision.html", context)




class TableroSalasView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CicloRevision
    pk_url_kwarg = 'ciclo_id'
    template_name = 'mantencion/pages/tablero_salas.html'
    context_object_name = 'ciclo'
    permission_required = 'mantencion.view_ciclomantenimiento'

    def get_queryset(self):
        return CicloRevision.objects.filter(tipo=CicloRevision.TipoCiclo.SALAS)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = self.object

        # 1. Traer todas las revisiones del ciclo optimizando las relaciones
        revisiones = (
            ciclo.revisiones_salas
            .select_related(
                'ubicacion',
                'ubicacion__piso',
                'ubicacion__piso__edificio',
                'proyector',
                'proyector__catalogo',
                'proyector__catalogo__marca',
                'operador'
            )
            .order_by(
                'ubicacion__piso__edificio__nombre',
                'ubicacion__piso__nombre',
                'ubicacion__nombre'
            )
        )

        # 2. Agrupación jerárquica en memoria: Edificio -> Piso -> Salas
        edificios_dict = {}

        for rev in revisiones:
            ubicacion = rev.ubicacion
            piso = ubicacion.piso
            edificio = piso.edificio if piso else None

            ed_id = edificio.id if edificio else 0
            ed_nombre = edificio.nombre if edificio else "Sin Edificio Asignado"

            if ed_id not in edificios_dict:
                edificios_dict[ed_id] = {
                    'id': ed_id,
                    'nombre': ed_nombre,
                    'total': 0,
                    'revisadas': 0,
                    'criticas': 0,
                    'con_observaciones': 0,
                    'pisos': {}
                }

            piso_id = piso.id if piso else 0
            piso_nombre = piso.nombre if piso else "Sin Piso"

            if piso_id not in edificios_dict[ed_id]['pisos']:
                edificios_dict[ed_id]['pisos'][piso_id] = {
                    'id': piso_id,
                    'nombre': piso_nombre,
                    'total': 0,
                    'revisadas': 0,
                    'salas': []
                }

            # Acumuladores de métricas
            es_revisada = rev.estado_general != RevisionSala.EstadoGeneralSala.PENDIENTE

            edificios_dict[ed_id]['total'] += 1
            edificios_dict[ed_id]['pisos'][piso_id]['total'] += 1

            if es_revisada:
                edificios_dict[ed_id]['revisadas'] += 1
                edificios_dict[ed_id]['pisos'][piso_id]['revisadas'] += 1

            if rev.estado_general == RevisionSala.EstadoGeneralSala.CRITICA:
                edificios_dict[ed_id]['criticas'] += 1
            elif rev.estado_general == RevisionSala.EstadoGeneralSala.CON_OBSERVACIONES:
                edificios_dict[ed_id]['con_observaciones'] += 1

            # Incorporar la revisión a la lista
            edificios_dict[ed_id]['pisos'][piso_id]['salas'].append(rev)

        # 3. Convertir a listas ordenadas para renderizar fácilmente en el template
        arbol_edificios = []
        for ed in edificios_dict.values():
            ed['pisos_lista'] = list(ed['pisos'].values())
            # Porcentaje de avance por edificio
            ed['porcentaje'] = round((ed['revisadas'] / ed['total']) * 100) if ed['total'] > 0 else 0
            for p in ed['pisos_lista']:
                p['porcentaje'] = round((p['revisadas'] / p['total']) * 100) if p['total'] > 0 else 0
            arbol_edificios.append(ed)

        context['arbol_edificios'] = arbol_edificios
        context['titulo_pagina'] = f"Tablero: {ciclo.nombre}"
        return context

class FragmentoTableroSalasView(View):
    def get():
        pass




class FormularioRevisionSalaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'mantencion.change_revisionsala'

    def get_proyector_inventario(self, ubicacion):
        """Busca el proyector que el inventario general registra actualmente en esta sala."""
        return Activo.objects.filter(
            ubicacion=ubicacion,
            catalogo__categoria__nombre__icontains="proyect",
            is_deleted=False
        ).select_related('catalogo', 'catalogo__marca').first()

    def get_proyectores_inventario(self, ubicacion):
        """Retorna todos los proyectores asignados actualmente a la sala de forma determinista."""
        return list(Activo.objects.filter(
            ubicacion=ubicacion,
            catalogo__categoria__nombre__icontains="proyect",
            is_deleted=False
        ).select_related('catalogo', 'catalogo__marca').order_by('-id'))

    def get(self, request, pk):
        revision = get_object_or_404(
            RevisionSala.objects.select_related(
                'ciclo',
                'ubicacion',
                'ubicacion__piso',
                'ubicacion__piso__edificio',
                'proyector',
                'proyector__catalogo',
                'proyector__catalogo__marca'
            ),
            pk=pk
        )

        proyectores_inventario = self.get_proyectores_inventario(revision.ubicacion)
        ids_en_inventario = [p.id for p in proyectores_inventario]

        hay_discrepancia = False
        proyector_sugerido = None

        if revision.proyector_id:
            # Si el proyector de la revisión ya no está entre los activos de la sala
            if revision.proyector_id not in ids_en_inventario:
                hay_discrepancia = True
                proyector_sugerido = proyectores_inventario[0] if proyectores_inventario else None
        else:
            # Si la revisión estaba sin proyector pero ahora inventario sí tiene
            if proyectores_inventario:
                hay_discrepancia = True
                proyector_sugerido = proyectores_inventario[0]

        form = RevisionSalaForm(instance=revision)
        context = {
            'revision': revision,
            'ciclo': revision.ciclo,
            'ubicacion': revision.ubicacion,
            'proyector_actual': revision.proyector,
            'proyector_inventario': proyector_sugerido,
            'proyectores_sala': proyectores_inventario,
            'hay_multiples': len(proyectores_inventario) > 1,
            'hay_discrepancia': hay_discrepancia,
            'form': form,
            'titulo': f"Revisión {revision.ubicacion.nombre}",
        }
        return render(request, 'mantencion/pages/revisar_sala.html', context)

    def post(self, request, pk):
        print("--- DEBUG POST ---")
        print("request.POST:", request.POST)
        print("------------------")

        revision = get_object_or_404(
            RevisionSala.objects.select_related('ciclo', 'ubicacion'),
            pk=pk
        )

        form = RevisionSalaForm(request.POST, instance=revision)
        if form.is_valid():
            rev = form.save(commit=False)
            rev.operador = request.user
            rev.fecha_revision = timezone.now()

            # Si el técnico declaró sin proyector, nos aseguramos de limpiar sus semáforos
            if not rev.proyector:
                rev.proyector_encendido = None
                rev.horas_lampara = None
                rev.red_proyector_conectada = None
                rev.proyeccion_inalambrica = None
                rev.candado_proyector = None

            rev.save() # Guarda y calcula el estado_general automáticamente

            messages.success(
                request,
                f"Revisión de {revision.ubicacion.nombre} guardada exitosamente como '{rev.get_estado_general_display()}'."
            )
            return redirect('mantencion:tablero_salas', ciclo_id=revision.ciclo_id)

        proyector_inventario = self.get_proyector_inventario(revision.ubicacion)
        context = {
            'revision': revision,
            'ciclo': revision.ciclo,
            'ubicacion': revision.ubicacion,
            'proyector_actual': revision.proyector,
            'proyector_inventario': proyector_inventario,
            'hay_discrepancia': (revision.proyector_id != (proyector_inventario.id if proyector_inventario else None)),
            'form': form,
            'titulo': f"Revisión {revision.ubicacion.nombre}",
        }
        return render(request, 'mantencion/pages/revisar_sala.html', context)




class TableroImpresorasView(View):
    def get():
        pass

class FormularioRevisionImpresoraView(View):
    def get():
        pass

class GenerarReportePdfView(View):
    def get():
        pass

class ExportarExcelRevisionView(View):
    def get():
        pass

class FirmarSubidaCloudinaryView(LoginRequiredMixin, View):
    def get(self, request):
        sala_id = request.GET.get('sala_id')
        revision = get_object_or_404(
            RevisionSala.objects.select_related('ubicacion'), 
            pk=sala_id
        )

        # Generar identificador único normalizado
        ahora = timezone.now()
        periodo = ahora.strftime('%Y-%m')
        hora_marca = ahora.strftime('%H%M%S')
        sala_slug = slugify(revision.ubicacion.nombre)

        # Nombre sin extensión (Cloudinary la añade sola)
        public_id = f"evidencia_{periodo}_{sala_slug}_{hora_marca}"
        folder = "evidencias_salas"
        timestamp = int(time.time())

        params_a_firmar = {
            'timestamp': timestamp,
            'folder': folder,
            'public_id': public_id,
        }

        # Generar firma incluyendo el public_id
        storage_settings = getattr(settings, 'CLOUDINARY_STORAGE', {})
        api_secret = storage_settings.get('API_SECRET') or cloudinary.config().api_secret
        signature = cloudinary.utils.api_sign_request(params_a_firmar, api_secret)

        return JsonResponse({
            'signature': signature,
            'timestamp': timestamp,
            'api_key': storage_settings.get('API_KEY') or cloudinary.config().api_key,
            'cloud_name': storage_settings.get('CLOUD_NAME') or cloudinary.config().cloud_name,
            'folder': folder,
            'public_id': public_id,
        })




class AsociarVideoSalaView(LoginRequiredMixin, View):
    """
    Recibe la URL devuelta por Cloudinary (o cualquier almacenamiento)
    y la asocia directamente a la RevisionSala correspondiente.
    """
    def post(self, request, pk):
        revision = get_object_or_404(RevisionSala, pk=pk)

        try:
            payload = json.loads(request.body)
            video_url = payload.get('video_url', '').strip()
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Formato JSON inválido.'}, status=400)

        if not video_url:
            return JsonResponse({'error': 'No se proporcionó una URL válida.'}, status=400)

        # Actualiza solo el campo de video
        revision.video_evidencia_url = video_url
        revision.save(update_fields=['video_evidencia_url'])

        return JsonResponse({
            'status': 'ok',
            'video_url': revision.video_evidencia_url
        })




@login_required
def subir_video_local(request, pk):
    """Guarda el video con nombre normalizado y lo asocia a la RevisionSala."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if not request.FILES.get('file'):
        return JsonResponse({'error': 'No se recibió ningún archivo de video.'}, status=400)

    revision = get_object_or_404(
        RevisionSala.objects.select_related('ciclo', 'ubicacion'), 
        pk=pk
    )
    video = request.FILES['file']

    # 1. Extraer extensión original (.mp4, .mov, etc.)
    _, ext = os.path.splitext(video.name)
    ext = ext.lower() if ext else '.mp4'

    # 2. Construir los componentes estandarizados
    ahora = timezone.now()
    periodo = ahora.strftime('%Y-%m')           # ej: '2026-11'
    hora_marca = ahora.strftime('%H%M%S')        # ej: '184522'
    sala_slug = slugify(revision.ubicacion.nombre) # ej: 'sala-301-a'

    # Nombre final: evidencia_2026-11_sala-301-a_184522.mp4
    nombre_archivo = f"evidencia_{periodo}_{sala_slug}_{hora_marca}{ext}"
    ruta_relativa = os.path.join('evidencias_salas', nombre_archivo)

    # 3. Guardar y actualizar
    ruta_guardada = default_storage.save(ruta_relativa, video)
    url_publica = default_storage.url(ruta_guardada)

    revision.video_evidencia_url = url_publica
    revision.save(update_fields=['video_evidencia_url'])

    return JsonResponse({
        'status': 'ok',
        'secure_url': url_publica
    })