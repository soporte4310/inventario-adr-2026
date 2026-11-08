from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.views.generic import ListView, View

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

class TableroSalasView(View):
    def get():
        pass

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