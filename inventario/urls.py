from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    InicioNuevoView, 

    ListaActivosView, 
    AgregarActivoView, 
    EditarActivoView, 
    DetalleActivoView, 
    EliminarActivoView, 
    ActivosEliminadosListView, 

    SubirExcelActivosView, 
    DescargarExcelActivosView, 
    DescargarExcelFiltradoView, 
    DescargarPlantillaExcelView, 

    AuditoriaListView, 
    RestaurarActivoView,

    ListaCatalogoView,
    CrearCatalogoView,
    EditarCatalogoView

)


urlpatterns = [
    path('', InicioNuevoView.as_view(), name="inicio"),

    # Activos
    path('activos/', ListaActivosView.as_view(), name='lista_activos'),
    path('activos/nuevo/', AgregarActivoView.as_view(), name='agregar_activo'),
    path('activos/<int:pk>/editar/', EditarActivoView.as_view(), name='editar_activo'),
    path('activos/<int:pk>/', DetalleActivoView.as_view(), name='ver_activo'),
    path('activos/<int:pk>/eliminar/', EliminarActivoView.as_view(), name='eliminar_activo'),
    path('activos/eliminados/', ActivosEliminadosListView.as_view(), name='lista_eliminados'),
    path('activos/restaurar/<int:pk>/', RestaurarActivoView.as_view(), name='restaurar_activo'),

    # Catálogo
    path('catalogos/', ListaCatalogoView.as_view(), name='lista_catalogos'),
    path('catalogos/nuevo/', CrearCatalogoView.as_view(), name='agregar_catalogo'),
    path('catalogos/<int:pk>/editar/', EditarCatalogoView.as_view(), name='editar_catalogo'),

    # Excel
    path('activos/importar/', SubirExcelActivosView.as_view(), name='subir_excel_activos'),
    path('activos/descargar-plantilla/', DescargarPlantillaExcelView.as_view(), name='descargar_plantilla_excel'),
    path('activos/exportar/', DescargarExcelActivosView.as_view(), name='descargar_excel_activos'),
    path('activos/exportar-excel-filtrado/', DescargarExcelFiltradoView.as_view(), name='descargar_excel_filtrado'),

    # Historial
    path('auditoria/', AuditoriaListView.as_view(), name='lista_auditoria'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)