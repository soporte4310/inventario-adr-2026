from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    MantencionLoginView,
    HomeMantencionView,

    ListaProyectoresView,
    ListaImpresorasView,
    ListaExcelProyectoresView,
    ListaExcelImpresoresView,

    RevisionProyectoresView,
    RevisionImpresorasView,
    NuevoCicloProyectoresView,
    NuevoCicloImpresorasView,
    MarcarOkView,
    RegistrarNovedadView,
    EnroqueView,

    ReporteExcelProyectoresView,
    ReporteExcelImpresoresView,
    ReporteEmailProyectoresView,
    ReporteEmailImpresoresView,

    RosterEquiposView,
    RosterAgregarEquipoView,
    RosterPausarEquipoView,

    ImpresoraAgregarView,

    AuditoriaMantencionView,
)


urlpatterns = [
    # Puerta de entrada propia de Mantención: misma autenticación que
    # inventario, pero aterriza en /mantencion/ (no en /inventario/) y
    # vuelve acá al cerrar sesión.
    path('login/', MantencionLoginView.as_view(), name='mantencion_login'),
    path('logout/', LogoutView.as_view(next_page='mantencion_login'), name='mantencion_logout'),

    path('', HomeMantencionView.as_view(), name='mantencion_home'),

    # Listas informativas
    path('proyectores/', ListaProyectoresView.as_view(), name='mantencion_lista_proyectores'),
    path('impresoras/', ListaImpresorasView.as_view(), name='mantencion_lista_impresoras'),
    path('proyectores/excel/', ListaExcelProyectoresView.as_view(), name='mantencion_lista_excel_proyectores'),
    path('impresoras/excel/', ListaExcelImpresoresView.as_view(), name='mantencion_lista_excel_impresoras'),

    # Revisión mensual
    path('revision/proyectores/', RevisionProyectoresView.as_view(), name='mantencion_revision_proyectores'),
    path('revision/impresoras/', RevisionImpresorasView.as_view(), name='mantencion_revision_impresoras'),
    path('revision/proyectores/nuevo-ciclo/', NuevoCicloProyectoresView.as_view(), name='mantencion_nuevo_ciclo_proyectores'),
    path('revision/impresoras/nuevo-ciclo/', NuevoCicloImpresorasView.as_view(), name='mantencion_nuevo_ciclo_impresoras'),
    path('revision/<int:pk>/ok/', MarcarOkView.as_view(), name='mantencion_marcar_ok'),
    path('revision/<int:pk>/novedad/', RegistrarNovedadView.as_view(), name='mantencion_registrar_novedad'),
    path('revision/equipo/<int:equipo_id>/enroque/', EnroqueView.as_view(), name='mantencion_enroque'),

    # Reportes
    path('revision/proyectores/excel/', ReporteExcelProyectoresView.as_view(), name='mantencion_reporte_excel_proyectores'),
    path('revision/impresoras/excel/', ReporteExcelImpresoresView.as_view(), name='mantencion_reporte_excel_impresoras'),
    path('revision/proyectores/email/', ReporteEmailProyectoresView.as_view(), name='mantencion_reporte_email_proyectores'),
    path('revision/impresoras/email/', ReporteEmailImpresoresView.as_view(), name='mantencion_reporte_email_impresoras'),

    # Roster de equipos en mantención (sólo ADR)
    path('roster/', RosterEquiposView.as_view(), name='mantencion_roster'),
    path('roster/nuevo/', RosterAgregarEquipoView.as_view(), name='mantencion_roster_agregar'),
    path('roster/<int:pk>/pausar/', RosterPausarEquipoView.as_view(), name='mantencion_roster_pausar'),

    # Alta de impresoras (modal en Lista de impresoras, sólo ADR). La baja se
    # maneja con "Quitar" (pausar) por fila + el modal "De baja" para verlas.
    path('impresoras/agregar/', ImpresoraAgregarView.as_view(), name='mantencion_impresora_agregar'),

    # Bitácora de auditoría (solo lectura, solo ADR)
    path('auditoria/', AuditoriaMantencionView.as_view(), name='mantencion_auditoria'),
]
