from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.views.generic import ListView, DetailView, View

from .models import CicloRevision, RevisionSala

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
        context['titulo_lista'] = 'Historial de Ciclos Preventivos'

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

class CerrarRevisionView(View):
    def get():
        pass

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

class FormularioRevisionSalaView(View):
    def get():
        pass

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

class FirmarSubidaCloudinaryView(View):
    def get():
        pass