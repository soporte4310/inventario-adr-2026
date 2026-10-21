from django.urls import path
from .views import *

urlpatterns = [
    # Funcionalidades de webeo (Ignorar)
    path('blacklist830/', ListaNegraView.as_view(), name='lista_negra'),
    path('blacklist830/agregar/', AgregarAListaNegraView.as_view(), name='agregar_lista_negra'),
    path('blacklist830/<int:pk>/eliminar/', EliminarDeListaNegraView.as_view(), name='eliminar_lista_negra'),
    path('blacklist830/reporte-pdf/', ReporteListaNegraPDFView.as_view(), name='reporte_pdf'),

    path('blacklist830/<int:pk>/', DetalleExpedienteView.as_view(), name='detalle_expediente'),
    path('blacklist830/<int:pk>/agregar-falta/', AgregarFaltaView.as_view(), name='agregar_falta'),
    path('blacklist830/falta/<int:falta_id>/eliminar/', EliminarFaltaView.as_view(), name='eliminar_falta'),
]