import os
import re
import json
import time
import cloudinary
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Prefetch
from django.views.generic import ListView, DetailView, View, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.http import JsonResponse

from django.core.exceptions import ValidationError
from .models import CicloRevision, RevisionSala
from .forms import CerrarRevisionForm, RevisionSalaForm
from inventario.models import Activo, Edificio, Piso, Ubicacion
from .utils import procesar_miniatura_revision_sala
from common.validators import validar_archivo_video
from .services import crear_ciclo_extraordinario_salas, MESES_ES

class DashboardInventario(TemplateView):
    template_name = 'mantencion/pages/dashboard.html'




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




class CrearRevisionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Permite exclusivamente al superusuario crear un ciclo extraordinario de salas."""

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(
            self.request,
            "Acceso denegado: Solo los administradores / superusuarios pueden iniciar un ciclo extraordinario.",
        )
        return redirect("mantencion:lista_revisiones")

    def _obtener_ciclo_vigente_mes(self):
        hoy = timezone.localdate()
        return CicloRevision.objects.filter(
            tipo=CicloRevision.TipoCiclo.SALAS,
            estado=CicloRevision.EstadoCiclo.EN_CURSO,
            fecha_inicio__year=hoy.year,
            fecha_inicio__month=hoy.month
        ).first()

    def get(self, request):
        ciclo_vigente = self._obtener_ciclo_vigente_mes()
        if ciclo_vigente:
            messages.warning(
                request,
                f"No se puede iniciar un ciclo extraordinario: el ciclo '{ciclo_vigente.nombre}' se encuentra en curso."
            )
            return redirect("mantencion:lista_revisiones")

        hoy = timezone.localdate()
        total_salas = Ubicacion.objects.filter(
            tipo=Ubicacion.TipoUbicacion.SALA_CLASES,
            aplica_mantenimiento=True
        ).count()

        context = {
            'titulo': 'Iniciar Ciclo Extraordinario de Salas',
            'mes_nombre': MESES_ES[hoy.month],
            'anio': hoy.year,
            'total_salas': total_salas,
        }
        return render(request, 'mantencion/pages/crear_revision.html', context)

    def post(self, request):
        nombre_personalizado = request.POST.get('nombre', '').strip()
        
        exito, mensaje, ciclo = crear_ciclo_extraordinario_salas(
            usuario=request.user,
            nombre_personalizado=nombre_personalizado or None
        )

        if not exito:
            messages.error(request, mensaje)
            return redirect("mantencion:lista_revisiones")

        messages.success(request, mensaje)
        return redirect("mantencion:tablero_salas", ciclo_id=ciclo.id)


    

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




@login_required
def subir_video_local(request, pk):
    """Guarda el video validado y genera las miniaturas de evidencia."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if not request.FILES.get('file'):
        return JsonResponse({'error': 'No se recibió ningún archivo de video.'}, status=400)

    revision = get_object_or_404(
        RevisionSala.objects.select_related('ciclo', 'ubicacion'), 
        pk=pk
    )
    video = request.FILES['file']

    # 1. Validar video en servidor
    try:
        validar_archivo_video(video)
    except ValidationError as e:
        return JsonResponse({'error': e.messages[0]}, status=400)

    # 2. Guardar archivo de video
    _, ext = os.path.splitext(video.name)
    ext = ext.lower() if ext else '.mp4'

    ahora = timezone.now()
    periodo = ahora.strftime('%Y-%m')
    hora_marca = ahora.strftime('%H%M%S')
    sala_slug = slugify(revision.ubicacion.nombre)

    nombre_archivo = f"evidencia_{periodo}_{sala_slug}_{hora_marca}{ext}"
    ruta_relativa = os.path.join('evidencias_salas', nombre_archivo)

    ruta_guardada = default_storage.save(ruta_relativa, video)
    url_publica = default_storage.url(ruta_guardada)
    revision.video_evidencia_url = url_publica

    # 3. Procesar miniatura recibida desde el frontend
    thumbnail_file = request.FILES.get('thumbnail')
    if thumbnail_file:
        procesar_miniatura_revision_sala(revision, thumbnail_file, prefix=f"sala_{sala_slug}")
        revision.save()
    else:
        revision.save(update_fields=['video_evidencia_url'])

    return JsonResponse({
        'status': 'ok',
        'secure_url': revision.video_evidencia_url,
        'video_url': revision.video_evidencia_url,
        'thumb_url': revision.imagen_thumb_small.url if revision.imagen_thumb_small else '',
        'estado_general': revision.estado_general,
        'checklist_completado': revision.checklist_completado,
    })




def eliminar_archivo_video_evidencia(video_url):
    """
    Elimina físicamente el archivo de video ya sea que esté
    almacenado en Cloudinary o en el almacenamiento local.
    """
    if not video_url:
        return

    try:
        # Caso 1: Video en Cloudinary
        if 'cloudinary.com' in video_url:
            # Extraer el public_id (ej: 'evidencias_salas/evidencia_2026-11_sala-1_123456')
            # Busca lo que esté tras '/upload/(v12345/)?' excluyendo la extensión (.mp4, etc.)
            match = re.search(r'/upload/(?:v\d+/)?([^\.]+)', video_url)
            if match:
                public_id = match.group(1)
                cloudinary.uploader.destroy(public_id, resource_type="video")

        # Caso 2: Almacenamiento local (MEDIA_ROOT / default_storage)
        else:
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            ruta_relativa = video_url
            if video_url.startswith(media_url):
                ruta_relativa = video_url[len(media_url):]

            ruta_relativa = ruta_relativa.lstrip('/')

            if default_storage.exists(ruta_relativa):
                default_storage.delete(ruta_relativa)

    except Exception as e:
        # Se captura para que una falla externa de red no impida restablecer la revisión
        print(f"[ADVERTENCIA] No se pudo eliminar el video ({video_url}): {e}")




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

            if rev.tiene_video:
                messages.success(
                    request,
                    f"Revisión de {revision.ubicacion.nombre} completada exitosamente como '{rev.get_estado_general_display()}'."
                )
            else:
                messages.warning(
                    request,
                    f"Checklist de {revision.ubicacion.nombre} guardado. Falta subir el video de evidencia para completar la revisión."
                )
            return redirect('mantencion:tablero_salas', ciclo_id=revision.ciclo_id)

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




class RestablecerRevisionSalaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Invalida y limpia una revisión previamente realizada, borrando
    la evidencia multimedia asociada y devolviendo el registro al estado 'PENDIENTE'.
    """
    permission_required = 'mantencion.change_revisionsala'

    def post(self, request, pk):
        revision = get_object_or_404(
            RevisionSala.objects.select_related('ciclo', 'ubicacion'),
            pk=pk
        )

        if revision.ciclo.estado == CicloRevision.EstadoCiclo.FINALIZADO:
            messages.error(request, "No es posible restablecer una sala de un ciclo ya cerrado.")
            return redirect('mantencion:revisar_sala', pk=revision.id)

        # 1. Eliminar físicamente el video de Cloudinary o del disco si existía
        if revision.video_evidencia_url:
            eliminar_archivo_video_evidencia(revision.video_evidencia_url)

        # 2. Obtener el proyector que figura actualmente en inventario para esta sala
        proyector_inventario = Activo.objects.filter(
            ubicacion=revision.ubicacion,
            catalogo__categoria__nombre__icontains="proyect",
            is_deleted=False
        ).first()

        if revision.imagen_evidencia:
            revision.imagen_evidencia.delete(save=False)
        if revision.imagen_thumb_medium:
            revision.imagen_thumb_medium.delete(save=False)
        if revision.imagen_thumb_small:
            revision.imagen_thumb_small.delete(save=False)

        # 3. Limpieza en base de datos devolviendo a PENDIENTE
        RevisionSala.objects.filter(pk=revision.pk).update(
            proyector=proyector_inventario,
            proyector_encendido=None,
            horas_lampara=None,
            red_proyector_conectada=None,
            proyeccion_inalambrica=None,
            candado_proyector=None,
            copla_hdmi=None,
            panel_control=None,
            puerto_red_pared=None,
            audio_sala=None,
            observaciones="",
            operador=None,
            fecha_revision=None,
            video_evidencia_url=None,
            imagen_evidencia=None,
            imagen_thumb_medium=None,
            imagen_thumb_small=None,
            estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE
        )

        messages.info(
            request,
            f"La revisión de la sala '{revision.ubicacion.nombre}' fue restablecida a Pendiente y se purgó la evidencia asociada."
        )
        return redirect('mantencion:revisar_sala', pk=revision.id)




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
    def post(self, request, pk):
        revision = get_object_or_404(RevisionSala, pk=pk)

        video_url = request.POST.get('video_url', '').strip()
        duracion_raw = request.POST.get('duration')
        thumbnail_file = request.FILES.get('thumbnail')

        if not video_url:
            return JsonResponse({'error': 'No se proporcionó una URL válida.'}, status=400)

        # Validar duración reportada por Cloudinary (31.5s máx.)
        if duracion_raw:
            try:
                duracion = float(duracion_raw)
                if duracion > 31.5:
                    # Borramos de Cloudinary el archivo que excedió el tiempo
                    eliminar_archivo_video_evidencia(video_url)
                    return JsonResponse({
                        'error': f'El video dura {round(duracion)}s y supera el máximo permitido de 30 segundos.'
                    }, status=400)
            except ValueError:
                pass

        # Si ya había un video anterior en la sala, lo eliminamos antes de reemplazarlo
        if revision.video_evidencia_url and revision.video_evidencia_url != video_url:
            eliminar_archivo_video_evidencia(revision.video_evidencia_url)

        revision.video_evidencia_url = video_url

        if thumbnail_file:
            sala_slug = slugify(revision.ubicacion.nombre)
            procesar_miniatura_revision_sala(revision, thumbnail_file, prefix=f"sala_{sala_slug}")
            revision.save()
        else:
            revision.save(update_fields=['video_evidencia_url'])

        return JsonResponse({
            'status': 'ok',
            'video_url': revision.video_evidencia_url,
            'thumb_url': revision.imagen_thumb_small.url if revision.imagen_thumb_small else '',
            'estado_general': revision.estado_general,
            'checklist_completado': revision.checklist_completado,
        })




class SalasMantenimientoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Ubicacion
    template_name = 'mantencion/pages/salas_mantenimiento.html'
    context_object_name = 'ubicaciones'
    paginate_by = 20
    permission_required = 'mantencion.view_revisionsala'

    def get_ciclo_activo(self):
        """Retorna el ciclo de salas actualmente en curso (o None si no hay uno abierto)."""
        if not hasattr(self, '_ciclo_activo'):
            self._ciclo_activo = CicloRevision.objects.filter(
                tipo=CicloRevision.TipoCiclo.SALAS,
                estado=CicloRevision.EstadoCiclo.EN_CURSO
            ).first()
        return self._ciclo_activo

    def get_queryset(self):
        ciclo_activo = self.get_ciclo_activo()

        # 1. Filtramos solo recintos que forman parte del ciclo preventivo
        queryset = Ubicacion.objects.filter(aplica_mantenimiento=True).select_related(
            'piso', 
            'piso__edificio'
        )

        # 2. Si hay ciclo en curso, prefetcheamos la revisión correspondiente a este ciclo
        if ciclo_activo:
            queryset = queryset.prefetch_related(
                Prefetch(
                    'revisiones_mantenimiento',
                    queryset=RevisionSala.objects.filter(ciclo=ciclo_activo).select_related('proyector', 'operador'),
                    to_attr='revision_actual_lista'
                )
            )

        # 3. Parámetros GET
        search_query = self.request.GET.get('search', '').strip()
        edificio_id = self.request.GET.get('edificio', '').strip()
        piso_nombre = self.request.GET.get('piso', '').strip()

        # 4. Filtros dinámicos
        if search_query:
            queryset = queryset.filter(nombre__icontains=search_query)

        if edificio_id:
            queryset = queryset.filter(piso__edificio_id=edificio_id)

        if piso_nombre:
            queryset = queryset.filter(piso__nombre=piso_nombre)

        return queryset.order_by('piso__edificio__nombre', 'piso__nombre', 'nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo_activo = self.get_ciclo_activo()
        
        context['titulo_lista'] = 'Salas de Clases'
        context['ciclo_activo'] = ciclo_activo

        # Preservar valores de filtros para formularios
        search_query = self.request.GET.get('search', '').strip()
        edificio_id = self.request.GET.get('edificio', '').strip()
        piso_nombre = self.request.GET.get('piso', '').strip()

        context['search_query'] = search_query
        context['edificio_id'] = edificio_id
        context['piso_nombre'] = piso_nombre

        # Listados para selects
        context['edificios'] = Edificio.objects.all()
        context['pisos'] = Piso.objects.values_list('nombre', flat=True).distinct().order_by('nombre')

        # Reconstruir query_string dinámicamente para conservar filtros en paginación
        query_params = []
        if search_query: 
            query_params.append(f'search={search_query}')
        if edificio_id: 
            query_params.append(f'edificio={edificio_id}')
        if piso_nombre: 
            query_params.append(f'piso={piso_nombre}')

        context['query_string'] = '&' + '&'.join(query_params) if query_params else ''

        return context




class VideoValidationFormMixin:
    """
    Mixin para formularios que valida de forma automática cualquier
    campo FileField/CharField que reciba un archivo de video.
    """
    def clean(self):
        cleaned_data = super().clean()
        for field_name, field in self.fields.items():
            if isinstance(field, forms.FileField):
                archivo = self.files.get(field_name)
                if archivo and isinstance(archivo, UploadedFile):
                    try:
                        validar_archivo_video(archivo)
                    except ValidationError as e:
                        mensaje = e.messages[0] if hasattr(e, 'messages') else str(e)
                        self.add_error(field_name, mensaje)
        return cleaned_data