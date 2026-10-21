from django.urls import path
from . import views

urlpatterns = [
    # Funcionalidades de webeo (Ignorar)
    path('blacklist830/', views.lista_negra_view, name='lista_negra'),
    path('blacklist830/agregar/', views.agregar_a_lista_negra, name='agregar_lista_negra'),
    path('blacklist830/<int:pk>/eliminar/', views.eliminar_de_lista_negra, name='eliminar_lista_negra'),
    path('blacklist830/reporte-pdf/', views.reporte_lista_negra_pdf, name='reporte_pdf'),

    path('blacklist830/<int:pk>/', views.detalle_expediente_view, name='detalle_expediente'),
    path('blacklist830/<int:pk>/agregar-falta/', views.agregar_falta, name='agregar_falta'),
    path('blacklist830/falta/<int:falta_id>/eliminar/', views.eliminar_falta, name='eliminar_falta'),
]