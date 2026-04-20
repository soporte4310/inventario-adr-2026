from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views import View
from django.views.generic import TemplateView, ListView, UpdateView, DetailView, CreateView, DeleteView

from ..models import Activo, Edificio, Piso, Ubicacion, Marca, Categoria, Estado
from ..forms import ActivoForm


# ---------------------------------------    
# NUEVAS VISTAS
# ---------------------------------------
class InicioNuevoView(LoginRequiredMixin, TemplateView):
    """
    Vista de inicio (Requiere Login)
    """
    template_name = 'home_nuevo.html'




class ListaActivosView(LoginRequiredMixin, ListView):
    """
    Vista unificada para listar activos con filtros avanzados por Query Params.
    Reemplaza a activo_list.
    """
    model = Activo
    template_name = 'lista_activos.html'
    paginate_by = 20
    context_object_name = 'page_obj'  # ListView utiliza 'page_obj' por defecto cuando hay paginación
    
    def get_queryset(self):
        # 1. Optimización de la consulta con select_related
        queryset = Activo.objects.select_related(
            'catalogo__categoria', 'catalogo__marca', 
            'ubicacion__piso__edificio', 'asignado_a', 'estado'
        ).all().order_by('-updated_at')
        
        # 2. Captura de parámetros GET y guardado en la instancia para usar en contexto
        self.search_query = self.request.GET.get('search', '')
        self.categoria_id = self.request.GET.get('categoria', '')
        self.categoria_nombre = self.request.GET.get('categoria_nombre', '')
        self.marca_id = self.request.GET.get('marca', '')
        self.estado_id = self.request.GET.get('estado', '')
        self.edificio_id = self.request.GET.get('edificio', '')
        self.ubicacion_nombre = self.request.GET.get('ubicacion_nombre', '')
        self.tipo_uso = self.request.GET.get('tipo_uso', '')
        self.tipo_red = self.request.GET.get('tipo_red', '')

        self.titulo_lista = "Listado General de Activos"

        # 3. Aplicación dinámica de filtros
        if self.categoria_id:
            queryset = queryset.filter(catalogo__categoria_id=self.categoria_id)
            try:
                cat_obj = Categoria.objects.get(id=self.categoria_id)
                self.titulo_lista = f"Inventario de {cat_obj.nombre}s"
            except Categoria.DoesNotExist:
                pass

        if self.categoria_nombre:
            queryset = queryset.filter(catalogo__categoria__nombre__icontains=self.categoria_nombre)
            self.titulo_lista = f"Inventario de {self.categoria_nombre}s"

        if self.marca_id:
            queryset = queryset.filter(catalogo__marca_id=self.marca_id)
            
        if self.estado_id:
            queryset = queryset.filter(estado_id=self.estado_id)
            
        if self.edificio_id:
            queryset = queryset.filter(ubicacion__piso__edificio_id=self.edificio_id)

        if self.ubicacion_nombre:
            queryset = queryset.filter(ubicacion__nombre__icontains=self.ubicacion_nombre)
            self.titulo_lista = f"Equipos en {self.ubicacion_nombre}"
            
        if self.tipo_uso:
            queryset = queryset.filter(tipo_uso=self.tipo_uso)
            if self.tipo_uso == Activo.TipoUso.EVENTOS:
                self.titulo_lista = "Equipos para Eventos"

        if self.tipo_red:
            queryset = queryset.filter(tipo_red=self.tipo_red)
            if self.tipo_red == Activo.TipoRed.ISLA:
                self.titulo_lista = "Equipos Isla"

        # 4. Búsqueda de texto global
        if self.search_query:
            queryset = queryset.filter(
                Q(numero_serie__icontains=self.search_query) |
                Q(etiqueta__icontains=self.search_query) |
                Q(bdo__icontains=self.search_query) |
                Q(netbios__icontains=self.search_query) |
                Q(asignado_a__nombre__icontains=self.search_query) |
                Q(catalogo__modelo__icontains=self.search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Preservar query params para la paginación
        get_copy = self.request.GET.copy()
        if 'page' in get_copy:
            get_copy.pop('page')
        query_string = get_copy.urlencode()

        context.update({
            'titulo_lista': getattr(self, 'titulo_lista', "Listado General de Activos"),
            'query_string': f"&{query_string}" if query_string else "",
            
            # Listas para rellenar los select del HTML
            'categorias': Categoria.objects.all().order_by('nombre'),
            'marcas': Marca.objects.all().order_by('nombre'),
            'estados': Estado.objects.all().order_by('nombre'),
            'edificios': Edificio.objects.all().order_by('nombre'),
            'tipos_uso': Activo.TipoUso.choices,
            
            # Variables para mantener seleccionada la opción correcta en la vista
            'search_query': getattr(self, 'search_query', ''),
            'categoria_seleccionada': getattr(self, 'categoria_id', ''),
            'marca_seleccionada': getattr(self, 'marca_id', ''),
            'estado_seleccionado': getattr(self, 'estado_id', ''),
            'edificio_seleccionado': getattr(self, 'edificio_id', ''),
            'tipo_uso_seleccionado': getattr(self, 'tipo_uso', ''),
        })
        return context




class EditarActivoView(LoginRequiredMixin, UpdateView):
    """
    Vista unificada para editar cualquier tipo de activo.
    """
    pass




class DetalleActivoView(LoginRequiredMixin, DetailView):
    """
    Vista para mostrar el detalle completo de un activo.
    """
    pass




class AgregarActivoView(LoginRequiredMixin, CreateView):
    """
    Vista para registrar un nuevo activo.
    """
    pass


class EliminarActivoView(LoginRequiredMixin, DeleteView):
    """
    Vista para procesar la eliminación (soft-delete) de un activo.
    """
    pass


class SubirExcelActivosView(LoginRequiredMixin, View):
    """
    Vista para importar activos masivamente mediante Excel.
    Aplica reglas estrictas y mapea etiquetas legibles de vuelta a sus códigos internos.
    """
    pass

class DescargarPlantillaExcelView(LoginRequiredMixin, View):
    """
    Genera un archivo Excel (.xlsx) con las cabeceras correctas y listas desplegables
    basadas en los datos actuales del sistema (incluyendo etiquetas legibles para choices).
    """
    pass


class DescargarExcelActivosView(LoginRequiredMixin, View):
    """
    Vista para exportar todos los activos registrados en el sistema a un archivo Excel.
    """
    pass