from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    DashboardInventario, 

    ListaActivosView, 
    AgregarActivoView, 
    EditarActivoView, 
    DetalleActivoView, 
    EliminarActivoView, 
    EliminarActivosMasivoView,
    ActivosEliminadosListView, 

    SubirExcelActivosView, 
    DescargarExcelActivosView, 
    DescargarExcelFiltradoView, 
    DescargarPlantillaExcelView, 

    AuditoriaListView, 
    RestaurarActivoView,

    ListaCatalogoView,
    CrearCatalogoView,
    DetalleCatalogoView,
    EditarCatalogoView,
    EliminarCatalogoView,

    ListaCategoriaView,
    CrearCategoriaView,
    EditarCategoriaView,
    EliminarCategoriaView,
    DetalleCategoriaView,

    ListaAreaAdministrativaView,
    CrearAreaAdministrativaView,
    EditarAreaAdministrativaView,
    EliminarAreaAdministrativaView,

    ListaCargoView,
    CrearCargoView,
    EditarCargoView,
    EliminarCargoView,
)


urlpatterns = [
    path('', DashboardInventario.as_view(), name="dashboard_inventario"),

    # Activos
    path('activos/', ListaActivosView.as_view(), name='lista_activos'),
    path('activos/nuevo/', AgregarActivoView.as_view(), name='agregar_activo'),
    path('activos/<int:pk>/editar/', EditarActivoView.as_view(), name='editar_activo'),
    path('activos/<int:pk>/', DetalleActivoView.as_view(), name='ver_activo'),
    path('activos/<int:pk>/eliminar/', EliminarActivoView.as_view(), name='eliminar_activo'),
    path('activos/eliminar-masivo/', EliminarActivosMasivoView.as_view(), name='eliminar_activos_masivo'),
    path('activos/eliminados/', ActivosEliminadosListView.as_view(), name='lista_eliminados'),
    path('activos/restaurar/<int:pk>/', RestaurarActivoView.as_view(), name='restaurar_activo'),

    # Categorías
    path('categorias/', ListaCategoriaView.as_view(), name='lista_categorias'),
    path('categorias/nueva/', CrearCategoriaView.as_view(), name='agregar_categoria'),
    path('categorias/<int:pk>/editar/', EditarCategoriaView.as_view(), name='editar_categoria'),
    path('categorias/<int:pk>/eliminar/', EliminarCategoriaView.as_view(), name='eliminar_categoria'),
    path('categorias/<int:pk>/', DetalleCategoriaView.as_view(), name='ver_categoria'),

    # Catálogos
    path('catalogos/', ListaCatalogoView.as_view(), name='lista_catalogos'),
    path('catalogos/nuevo/', CrearCatalogoView.as_view(), name='agregar_catalogo'),
    path('catalogos/<int:pk>/', DetalleCatalogoView.as_view(), name='ver_catalogo'),
    path('catalogos/<int:pk>/editar/', EditarCatalogoView.as_view(), name='editar_catalogo'),
    path('catalogos/<int:pk>/eliminar/', EliminarCatalogoView.as_view(), name='eliminar_catalogo'),

    # Excel
    path('activos/importar/', SubirExcelActivosView.as_view(), name='subir_excel_activos'),
    path('activos/descargar-plantilla/', DescargarPlantillaExcelView.as_view(), name='descargar_plantilla_excel'),
    path('activos/exportar/', DescargarExcelActivosView.as_view(), name='descargar_excel_activos'),
    path('activos/exportar-excel-filtrado/', DescargarExcelFiltradoView.as_view(), name='descargar_excel_filtrado'),

    # Historial
    path('auditoria/', AuditoriaListView.as_view(), name='lista_auditoria'),

    # Áreas administrativas
    path('areas/', ListaAreaAdministrativaView.as_view(), name='lista_areas'),
    path('areas/nuevo/', CrearAreaAdministrativaView.as_view(), name='agregar_area'),
    path('areas/<int:pk>/', ListaAreaAdministrativaView.as_view(), name='ver_area'),
    path('areas/<int:pk>/editar/', EditarAreaAdministrativaView.as_view(), name='editar_area'),
    path('areas/<int:pk>/eliminar/', EliminarAreaAdministrativaView.as_view(), name='eliminar_area'),

    # Cargos de funcionarios
    path('cargos/', ListaCargoView.as_view(), name='lista_cargos'),
    path('cargos/nuevo/', CrearCargoView.as_view(), name='agregar_cargo'),
    path('cargos/<int:pk>/editar/', EditarCargoView.as_view(), name='editar_cargo'),
    path('cargos/<int:pk>/eliminar/', EliminarCargoView.as_view(), name='eliminar_cargo'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)