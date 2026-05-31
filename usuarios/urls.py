from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    ListaGruposView, 
    CrearGrupoView,
    EditarGrupoView,
)


urlpatterns = [
    # Gestión de grupos/roles
    path('grupos/', ListaGruposView.as_view(), name='lista_grupos'),
    path('grupos/nuevo/', CrearGrupoView.as_view(), name='agregar_grupo'),
    path('grupos/<int:pk>/editar/', EditarGrupoView.as_view(), name='editar_grupo'),
    path('grupos/<int:pk>/eliminar/', ListaGruposView.as_view(), name='eliminar_grupo'),
    path('grupos/<int:pk>/', ListaGruposView.as_view(), name='ver_grupo'),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)