from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import (
    DashboardMantencion,
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
    SubirVideoLocalView,
    AsociarVideoSalaView,
    RestablecerRevisionSalaView,
    SalasMantenimientoListView,
    RevisionActualView,
    ListaActividadMantencionView
)

app_name = "mantencion"

urlpatterns = [
    # Inicio
    path('', DashboardMantencion.as_view(), name="dashboard_mantenimiento"),

    # Historial y gestión de ciclos
    path("ciclos/", ListaRevisionesView.as_view(), name="lista_revisiones"),
    path("ciclos/crear/", CrearRevisionView.as_view(), name="crear_revision"),
    path("ciclos/<int:pk>/", DetalleRevisionView.as_view(), name="ver_revision"),
    path("ciclos/<int:pk>/cerrar/", CerrarRevisionView.as_view(), name="cerrar_revision"),

    # --- FLUJO 1: REVISIÓN DE SALAS DE CLASES ---
    # Salas incluidas en mantenimiento
    path('salas/', SalasMantenimientoListView.as_view(), name='salas_clases'),
    # Ciclo de revisión específico
    path('salas/ciclo/<int:ciclo_id>/', TableroSalasView.as_view(), name='tablero_salas'),
    # Revisión de sala específica
    path('salas/revision/<int:pk>/', FormularioRevisionSalaView.as_view(), name='revisar_sala'),
    # Reiniciar revisión de sala específica (incluye formulario y video)
    path('salas/revision/<int:pk>/restablecer/', RestablecerRevisionSalaView.as_view(), name='restablecer_sala'),
    # Subir video en entorno local
    path('salas/revision/<int:pk>/subir-video/', SubirVideoLocalView.as_view(), name='subir_video_local'),
    # Asociar video a sala
    path('salas/revision/<int:pk>/asociar-video/', AsociarVideoSalaView.as_view(), name='asociar_video_sala'),
    # Firmar video de evidencia para luego enviarlo a Cloudinary
    path('salas/firmar-cloudinary/', FirmarSubidaCloudinaryView.as_view(), name='firmar_cloudinary'),
    
    # --- FLUJO 2: REVISIÓN DE IMPRESORAS ---
    path('impresoras/ciclo/<int:ciclo_id>/', TableroImpresorasView.as_view(), name='tablero_impresoras'),
    path('impresoras/revision/<int:pk>/', FormularioRevisionImpresoraView.as_view(), name='revisar_impresora'),

    # Revisiones vigentes
    path('revision-actual/', RevisionActualView.as_view(), name='revision_actual'),
    
    # Reportes y exportación
    path("ciclos/<int:pk>/reporte-pdf/", GenerarReportePdfView.as_view(), name="reporte_pdf"),
    path("ciclos/<int:pk>/exportar-excel/", ExportarExcelRevisionView.as_view(), name="exportar_excel"),
    
    # Endpoints utilitarios
    path("api/firmar-cloudinary/", FirmarSubidaCloudinaryView.as_view(), name="firmar_cloudinary"),
    path("api/subir-video-local/<int:pk>/", SubirVideoLocalView.as_view(), name="subir_video_local"),
    path("api/asociar-video/<int:pk>/", AsociarVideoSalaView.as_view(), name="asociar_video"),

    # Registro de actividad
    path('actividad/', ListaActividadMantencionView.as_view(), name='registro_actividad'),

]
