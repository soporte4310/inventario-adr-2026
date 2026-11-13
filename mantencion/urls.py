from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import (
    DashboardInventario,
    ListaRevisionesView,
    CrearRevisionView,
    DetalleRevisionView,
    CerrarRevisionView,
    TableroSalasView,
    FragmentoTableroSalasView,
    FormularioRevisionSalaView,
    TableroImpresorasView,
    FormularioRevisionImpresoraView,
    GenerarReportePdfView,
    ExportarExcelRevisionView,
    FirmarSubidaCloudinaryView,
    subir_video_local,
    AsociarVideoSalaView,
    RestablecerRevisionSalaView,
    SalasMantenimientoListView
)

app_name = "mantencion"

urlpatterns = [
    # Inicio
    path('', DashboardInventario.as_view(), name="dashboard_mantenimiento"),

    # Historial y gestión de ciclos
    path("ciclos/", ListaRevisionesView.as_view(), name="lista_revisiones"),
    path("ciclos/crear/", CrearRevisionView.as_view(), name="crear_revision"),
    path("ciclos/<int:pk>/", DetalleRevisionView.as_view(), name="ver_revision"),
    path("ciclos/<int:pk>/cerrar/", CerrarRevisionView.as_view(), name="cerrar_revision"),

    # Revisión de Salas
    path("ciclos/<int:ciclo_id>/salas/", TableroSalasView.as_view(), name="tablero_salas"),
    path("ciclos/<int:ciclo_id>/salas/fragmento/", FragmentoTableroSalasView.as_view(), name="fragmento_tablero_salas"),
    path("revisiones/sala/<int:pk>/", FormularioRevisionSalaView.as_view(), name="revisar_sala"),
    path("revisiones/sala/<int:pk>/restablecer/", RestablecerRevisionSalaView.as_view(), name="restablecer_revision_sala"),
    
    # Revisión de Impresoras
    path("ciclos/<int:ciclo_id>/impresoras/", TableroImpresorasView.as_view(), name="tablero_impresoras"),
    path("revisiones/impresora/<int:pk>/", FormularioRevisionImpresoraView.as_view(), name="revisar_impresora"),
    
    # Reportes y exportación
    path("ciclos/<int:pk>/reporte-pdf/", GenerarReportePdfView.as_view(), name="reporte_pdf"),
    path("ciclos/<int:pk>/exportar-excel/", ExportarExcelRevisionView.as_view(), name="exportar_excel"),
    
    # Endpoints utilitarios
    path("api/firmar-cloudinary/", FirmarSubidaCloudinaryView.as_view(), name="firmar_cloudinary"),
    path("api/subir-video-local/<int:pk>/", subir_video_local, name="subir_video_local"),
    path("api/asociar-video/<int:pk>/", AsociarVideoSalaView.as_view(), name="asociar_video"),

    # Salas de clases
    path('salas/', SalasMantenimientoListView.as_view(), name='salas_clases'),

]
