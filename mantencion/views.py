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
from django.db.models import Count, Q, Case, When, IntegerField, Value, Prefetch
from django.views.generic import ListView, DetailView, View, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.http import JsonResponse

from django.core.exceptions import ValidationError
from .models import CicloRevision, RevisionSala, RevisionImpresora
from .forms import CerrarRevisionForm, RevisionSalaForm
from inventario.models import Activo, Edificio, Piso, Ubicacion
from .utils import procesar_miniatura_revision_sala
from common.validators import validar_archivo_video
from .services import crear_ciclo_extraordinario_salas, MESES_ES
from .mixins import CicloAbiertoRequiredMixin

class DashboardInventario(TemplateView):
    template_name = 'mantencion/pages/dashboard.html'




class ListaRevisionesView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CicloRevision
    template_name = 'mantencion/pages/lista_revisiones.html'
    context_object_name = 'revisiones'
    paginate_by = 15
    permission_required = 'mantencion.view_ciclorevision'

    def get_queryset(self):
        # Base con optimización de relaciones
        queryset = CicloRevision.objects.select_related('creado_por', 'cerrado_por')

        # Anotación condicional: según sea ciclo de salas o impresoras
        # (se anticipa la relación 'revisiones_impresoras' para cuando se cree el modelo)
        tiene_rev_impresoras = hasattr(CicloRevision, 'revisiones_impresoras')

        if tiene_rev_impresoras:
            queryset = queryset.annotate(
                total_items=Case(
                    When(tipo=CicloRevision.TipoCiclo.SALAS, then=Count('revisiones_salas', distinct=True)),
                    When(tipo=CicloRevision.TipoCiclo.IMPRESORAS, then=Count('revisiones_impresoras', distinct=True)),
                    default=Value(0),
                    output_field=IntegerField()
                ),
                completadas=Case(
                    When(
                        tipo=CicloRevision.TipoCiclo.SALAS,
                        then=Count('revisiones_salas', filter=~Q(revisiones_salas__estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE), distinct=True)
                    ),
                    When(
                        tipo=CicloRevision.TipoCiclo.IMPRESORAS,
                        then=Count('revisiones_impresoras', filter=~Q(revisiones_impresoras__estado_general='PENDIENTE'), distinct=True)
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        else:
            # Fallback seguro mientras se implementa el modelo RevisionImpresora
            queryset = queryset.annotate(
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

        # Filtros de búsqueda
        search_query = self.request.GET.get('search', '').strip()
        tipo_ciclo = self.request.GET.get('tipo', '').strip()
        estado_ciclo = self.request.GET.get('estado', '').strip()

        if search_query:
            queryset = queryset.filter(nombre__icontains=search_query)

        if tipo_ciclo in [CicloRevision.TipoCiclo.SALAS, CicloRevision.TipoCiclo.IMPRESORAS]:
            queryset = queryset.filter(tipo=tipo_ciclo)

        if estado_ciclo:
            queryset = queryset.filter(estado=estado_ciclo)

        return queryset.order_by('-fecha_inicio', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tipo_actual = self.request.GET.get('tipo', '').strip()

        # Título dinámico según la pestaña activa
        if tipo_actual == CicloRevision.TipoCiclo.SALAS:
            context['titulo_lista'] = 'Revisiones de Salas de Clases'
        elif tipo_actual == CicloRevision.TipoCiclo.IMPRESORAS:
            context['titulo_lista'] = 'Revisiones de Impresoras'
        else:
            context['titulo_lista'] = 'Historial General de Revisiones'

        # Conteos globales rápidos para las pestañas superiores
        base_qs = CicloRevision.objects.all()
        context['conteo_todos'] = base_qs.count()
        context['conteo_salas'] = base_qs.filter(tipo=CicloRevision.TipoCiclo.SALAS).count()
        context['conteo_impresoras'] = base_qs.filter(tipo=CicloRevision.TipoCiclo.IMPRESORAS).count()

        # Variables de estado y filtros
        context['search_query'] = self.request.GET.get('search', '').strip()
        context['tipo_ciclo'] = tipo_actual
        context['estado_ciclo'] = self.request.GET.get('estado', '').strip()
        context['estados'] = self.model.EstadoCiclo.choices

        # Construcción limpia de query string para paginación
        params = []
        if context['search_query']:
            params.append(f"search={context['search_query']}")
        if tipo_actual:
            params.append(f"tipo={tipo_actual}")
        if context['estado_ciclo']:
            params.append(f"estado={context['estado_ciclo']}")

        context['query_string'] = f"&{'&'.join(params)}" if params else ""
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
    permission_required = 'mantencion.view_ciclorevision'

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




class SubirVideoLocalView(LoginRequiredMixin, CicloAbiertoRequiredMixin, View):
    """Guarda el video validado localmente y genera las miniaturas de evidencia."""
    revision_model = RevisionSala

    def post(self, request, pk):
        if not request.FILES.get('file'):
            return JsonResponse({'error': 'No se recibió ningún archivo de video.'}, status=400)

        # self.revision ya viene cargada y validada (ciclo abierto) desde CicloAbiertoRequiredMixin
        revision = self.revision
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
    Elimina físicamente el archivo de video en Cloudinary o almacenamiento local,
    soportando URLs con parámetros de transformación.
    """
    if not video_url:
        return

    try:
        if 'cloudinary.com' in video_url:
            # Extrae 'evidencias_salas/nombre_archivo' ignorando parámetros intermedios y extensión
            match = re.search(r'(?:v\d+/)?(evidencias_salas/[^.]+)', video_url)
            if match:
                public_id = match.group(1)
                cloudinary.uploader.destroy(public_id, resource_type="video")
        else:
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            ruta_relativa = video_url
            if video_url.startswith(media_url):
                ruta_relativa = video_url[len(media_url):]

            ruta_relativa = ruta_relativa.lstrip('/')
            if default_storage.exists(ruta_relativa):
                default_storage.delete(ruta_relativa)

    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo eliminar el video ({video_url}): {e}")




class FormularioRevisionSalaView(LoginRequiredMixin, PermissionRequiredMixin, CicloAbiertoRequiredMixin, View):
    permission_required = 'mantencion.change_revisionsala'
    revision_model = RevisionSala
    permitir_lectura_get = True

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

        solo_lectura = revision.ciclo.esta_cerrado
        print(f"solo_lectura = {solo_lectura}")
        proyectores_inventario = self.get_proyectores_inventario(revision.ubicacion)
        ids_en_inventario = [p.id for p in proyectores_inventario]

        hay_discrepancia = False
        proyector_sugerido = None

        # Solo calculamos discrepancias de inventario si el ciclo sigue abierto
        if not solo_lectura:
            if revision.proyector_id:
                if revision.proyector_id not in ids_en_inventario:
                    hay_discrepancia = True
                    proyector_sugerido = proyectores_inventario[0] if proyectores_inventario else None
            else:
                if proyectores_inventario:
                    hay_discrepancia = True
                    proyector_sugerido = proyectores_inventario[0]

        form = RevisionSalaForm(instance=revision)

        # Si el ciclo está cerrado, deshabilitamos todos los campos del formulario
        if solo_lectura:
            for field in form.fields.values():
                field.disabled = True

        context = {
            'revision': revision,
            'ciclo': revision.ciclo,
            'ubicacion': revision.ubicacion,
            'proyector_actual': revision.proyector,
            'proyector_inventario': proyector_sugerido,
            'proyectores_sala': proyectores_inventario,
            'hay_multiples': len(proyectores_inventario) > 1,
            'hay_discrepancia': hay_discrepancia,
            'solo_lectura': solo_lectura,
            'form': form,
            'titulo': f"Detalle Revisión {revision.ubicacion.nombre}" if solo_lectura else f"Revisión {revision.ubicacion.nombre}",
        }
        return render(request, 'mantencion/pages/revisar_sala.html', context)

    def post(self, request, pk):
        revision = self.revision

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




class RestablecerRevisionSalaView(LoginRequiredMixin, PermissionRequiredMixin, CicloAbiertoRequiredMixin, View):
    """
    Invalida y limpia una revisión previamente realizada, borrando
    la evidencia multimedia asociada y devolviendo el registro al estado 'PENDIENTE'.
    """
    permission_required = 'mantencion.change_revisionsala'
    revision_model = RevisionSala

    def post(self, request, pk):
        revision = self.revision

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




class TableroImpresorasView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CicloRevision
    pk_url_kwarg = 'ciclo_id'
    template_name = 'mantencion/pages/tablero_impresoras.html'
    context_object_name = 'ciclo'
    permission_required = 'mantencion.view_ciclorevision'

    def get_queryset(self):
        return CicloRevision.objects.filter(tipo=CicloRevision.TipoCiclo.IMPRESORAS)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = self.object

        # 1. Recuperar todas las revisiones del ciclo optimizando relaciones
        revisiones = (
            ciclo.revisiones_impresoras
            .select_related(
                'impresora',
                'impresora__activo',
                'impresora__activo__catalogo',
                'impresora__activo__catalogo__marca',
                'impresora__activo__ubicacion',
                'impresora__activo__ubicacion__piso',
                'impresora__activo__ubicacion__piso__edificio',
                'operador'
            )
            .order_by(
                'impresora__activo__ubicacion__piso__edificio__nombre',
                'impresora__activo__ubicacion__piso__nombre',
                'impresora__activo__ubicacion__nombre',
                'impresora__activo__catalogo__modelo'
            )
        )

        # 2. Agrupación jerárquica en memoria: Edificio -> Piso -> Impresoras
        edificios_dict = {}

        for rev in revisiones:
            activo = rev.impresora.activo if hasattr(rev.impresora, 'activo') else None
            ubicacion = activo.ubicacion if activo else None
            piso = ubicacion.piso if ubicacion else None
            edificio = piso.edificio if piso else None

            ed_id = edificio.id if edificio else 0
            ed_nombre = edificio.nombre if edificio else "Sin Edificio Asignado"

            if ed_id not in edificios_dict:
                edificios_dict[ed_id] = {
                    'id': ed_id,
                    'nombre': ed_nombre,
                    'total': 0,
                    'revisadas': 0,
                    'operativas': 0,
                    'no_operativas': 0,
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
                    'impresoras': []
                }

            es_revisada = rev.estado_general != RevisionImpresora.EstadoGeneral.PENDIENTE

            edificios_dict[ed_id]['total'] += 1
            edificios_dict[ed_id]['pisos'][piso_id]['total'] += 1

            if es_revisada:
                edificios_dict[ed_id]['revisadas'] += 1
                edificios_dict[ed_id]['pisos'][piso_id]['revisadas'] += 1

            if rev.estado_general == RevisionImpresora.EstadoGeneral.OPERATIVA:
                edificios_dict[ed_id]['operativas'] += 1
            elif rev.estado_general == RevisionImpresora.EstadoGeneral.NO_OPERATIVA:
                edificios_dict[ed_id]['no_operativas'] += 1

            edificios_dict[ed_id]['pisos'][piso_id]['impresoras'].append(rev)

        # 3. Convertir a listas con cálculo de porcentaje para el render
        arbol_edificios = []
        for ed in edificios_dict.values():
            ed['pisos_lista'] = list(ed['pisos'].values())
            ed['porcentaje'] = round((ed['revisadas'] / ed['total']) * 100) if ed['total'] > 0 else 0
            for p in ed['pisos_lista']:
                p['porcentaje'] = round((p['revisadas'] / p['total']) * 100) if p['total'] > 0 else 0
            arbol_edificios.append(ed)

        context['arbol_edificios'] = arbol_edificios
        context['titulo_pagina'] = f"Tablero: {ciclo.nombre}"
        return context




class FormularioRevisionImpresoraView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Procesa la calificación operativa y las observaciones de una impresora,
    soportando peticiones asíncronas desde el modal del tablero o envíos estándar.
    """
    permission_required = 'mantencion.change_revisionimpresora'

    def post(self, request, pk):
        revision = get_object_or_404(
            RevisionImpresora.objects.select_related('ciclo', 'impresora__activo'),
            pk=pk
        )

        if revision.ciclo.esta_cerrado:
            return JsonResponse({'error': 'No se puede modificar una revisión de un ciclo finalizado.'}, status=400)

        operativa_param = request.POST.get('esta_operativa')
        observaciones = request.POST.get('observaciones', '').strip()

        if operativa_param in ['1', 'true', 'True']:
            revision.esta_operativa = True
        elif operativa_param in ['0', 'false', 'False']:
            revision.esta_operativa = False
        else:
            revision.esta_operativa = None

        revision.observaciones = observaciones
        revision.operador = request.user
        revision.fecha_revision = timezone.now() if revision.esta_operativa is not None else None
        revision.save()

        # Respuesta JSON para actualización reactiva en el tablero
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            fecha_str = timezone.localtime(revision.fecha_revision).strftime("%d/%m %H:%M") if revision.fecha_revision else ''
            return JsonResponse({
                'status': 'ok',
                'revision_id': revision.id,
                'esta_operativa': revision.esta_operativa,
                'estado_general': revision.estado_general,
                'estado_display': revision.get_estado_general_display(),
                'observaciones': revision.observaciones,
                'operador': revision.operador.username if revision.operador else '',
                'fecha_revision': fecha_str,
            })

        messages.success(request, f"Revisión de {revision.impresora} guardada correctamente.")
        return redirect('mantencion:tablero_impresoras', ciclo_id=revision.ciclo_id)




class RevisionActualView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Muestra los ciclos preventivos del mes en curso correspondientes a
    Salas de Clases e Impresoras, detallando su avance y acceso directo a tableros.
    """
    template_name = 'mantencion/pages/revision_actual.html'
    permission_required = 'mantencion.view_ciclorevision'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        mes_nombre = MESES_ES[hoy.month]

        # 1. Obtener los ciclos correspondientes al mes y año actual
        ciclo_salas = CicloRevision.objects.filter(
            tipo=CicloRevision.TipoCiclo.SALAS,
            fecha_inicio__year=hoy.year,
            fecha_inicio__month=hoy.month
        ).order_by('-id').first()

        ciclo_impresoras = CicloRevision.objects.filter(
            tipo=CicloRevision.TipoCiclo.IMPRESORAS,
            fecha_inicio__year=hoy.year,
            fecha_inicio__month=hoy.month
        ).order_by('-id').first()

        # 2. Estructuración modular de los ciclos del mes
        tarjetas_ciclos = [
            {
                'id_tipo': 'SALAS',
                'titulo': 'Revisión de Salas de Clases',
                'subtitulo': 'Inspección de equipamiento audiovisual, conectividad docente y proyector',
                'icono': 'fas fa-chalkboard-teacher',
                'color': 'primary',
                'color_hex': '#0d6efd',
                'ciclo': ciclo_salas,
                'url_tablero': 'mantencion:tablero_salas' if ciclo_salas else None,
                'total': ciclo_salas.total_salas if ciclo_salas else 0,
                'revisadas': ciclo_salas.total_revisadas if ciclo_salas else 0,
                'pendientes': ciclo_salas.total_pendientes if ciclo_salas else 0,
                'porcentaje': ciclo_salas.porcentaje_avance if ciclo_salas else 0,
                'metricas': [
                    {'label': 'Operativas', 'valor': ciclo_salas.total_operativas if ciclo_salas else 0, 'badge': 'bg-success text-white'},
                    {'label': 'Con Obs.', 'valor': ciclo_salas.total_con_observaciones if ciclo_salas else 0, 'badge': 'bg-warning text-dark'},
                    {'label': 'Críticas', 'valor': ciclo_salas.total_criticas if ciclo_salas else 0, 'badge': 'bg-danger text-white'},
                ]
            },
            {
                'id_tipo': 'IMPRESORAS',
                'titulo': 'Revisión de Impresoras',
                'subtitulo': 'Inspección técnica de flota y multifuncionales externos (SONDA / Contrato)',
                'icono': 'fas fa-print',
                'color': 'dark',
                'color_hex': '#212529',
                'ciclo': ciclo_impresoras,
                'url_tablero': 'mantencion:tablero_impresoras' if ciclo_impresoras else None,
                'total': ciclo_impresoras.total_impresoras if ciclo_impresoras else 0,
                'revisadas': ciclo_impresoras.total_impresoras_revisadas if ciclo_impresoras else 0,
                'pendientes': ciclo_impresoras.total_impresoras_pendientes if ciclo_impresoras else 0,
                'porcentaje': ciclo_impresoras.porcentaje_avance_impresoras if ciclo_impresoras else 0,
                'metricas': [
                    {'label': 'Operativas', 'valor': ciclo_impresoras.total_impresoras_operativas if ciclo_impresoras else 0, 'badge': 'bg-success text-white'},
                    {'label': 'Con Falla', 'valor': ciclo_impresoras.total_impresoras_no_operativas if ciclo_impresoras else 0, 'badge': 'bg-danger text-white'},
                ]
            }
        ]

        context.update({
            'titulo_pagina': f'Revisión Actual · {mes_nombre} {hoy.year}',
            'mes_nombre': mes_nombre,
            'anio_actual': hoy.year,
            'fecha_hoy': hoy,
            'tarjetas_ciclos': tarjetas_ciclos,
        })
        return context




class GenerarReportePdfView(View):
    def get():
        pass




class ExportarExcelRevisionView(View):
    def get():
        pass




class FirmarSubidaCloudinaryView(LoginRequiredMixin, CicloAbiertoRequiredMixin, View):
    revision_model = RevisionSala
    pk_url_kwarg = 'sala_id'

    def get(self, request):
        sala_id = request.GET.get('sala_id')
        revision = get_object_or_404(
            RevisionSala.objects.select_related('ubicacion'), 
            pk=sala_id
        )

        ahora = timezone.now()
        periodo = ahora.strftime('%Y-%m')
        hora_marca = ahora.strftime('%H%M%S')
        sala_slug = slugify(revision.ubicacion.nombre)

        public_id = f"evidencia_{periodo}_{sala_slug}_{hora_marca}"
        folder = "evidencias_salas"
        timestamp = int(time.time())
        
        # Redimensiona a 720p máximo y comprime con bitrate económico antes de guardar en disco
        #transformation = "c_limit,w_1280,q_auto:eco"

        # Transformación asíncrona recomendada por Cloudinary para videos pesados
        eager_transformation = "q_auto,vc_auto,w_1280,c_limit"

        params_a_firmar = {
            'timestamp': timestamp,
            'folder': folder,
            'public_id': public_id,
            #'transformation': transformation,
            'eager': eager_transformation,
            'eager_async': True,
        }

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
            #'transformation': transformation,
            'eager': eager_transformation,
            'eager_async': 'true',
        })




def optimizar_url_cloudinary_video(url):
    """
    Inyecta parámetros de compresión automática y escalado a 720p
    en la URL pública devuelta por Cloudinary.
    """
    if not url or 'cloudinary.com' not in url:
        return url

    # Evitamos duplicar parámetros si ya vienen en la URL
    if '/video/upload/q_auto' in url:
        return url

    return url.replace('/video/upload/', '/video/upload/q_auto,vc_auto,w_1280,c_limit/')



class AsociarVideoSalaView(LoginRequiredMixin, View):
    """
    Recibe la URL devuelta por Cloudinary junto con la miniatura
    y la asocia a la RevisionSala correspondiente.
    """
    def post(self, request, pk):
        revision = get_object_or_404(RevisionSala, pk=pk)

        # 1. Intentar obtener datos desde multipart (FormData)
        video_url = request.POST.get('video_url', '').strip()
        thumbnail_file = request.FILES.get('thumbnail')

        # 2. Si no viene en POST, intentar leer JSON como fallback
        if not video_url and request.body:
            try:
                payload = json.loads(request.body)
                video_url = payload.get('video_url', '').strip()
            except (json.JSONDecodeError, AttributeError):
                pass

        if not video_url:
            return JsonResponse({'error': 'No se proporcionó una URL válida de video.'}, status=400)

        # Si ya había un video anterior en Cloudinary, se elimina para no acumular basura
        if revision.video_evidencia_url and revision.video_evidencia_url != video_url:
            eliminar_archivo_video_evidencia(revision.video_evidencia_url)

        video_url = optimizar_url_cloudinary_video(video_url)
        revision.video_evidencia_url = video_url

        # 3. Procesar miniatura si viene en la petición
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