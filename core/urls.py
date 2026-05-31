
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='inventario/', permanent=False), name='index_redirect'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('adr/', include('adr.urls')),
    path("__reload__/", include("django_browser_reload.urls")), # RECARGA LA PAGINA EN TIEMPO REAL CUANDO SE REALIZAN CAMBIOS
    
    # Rutas de Gestión de inventario
    path('inventario/', include('inventario.urls')),
    # Rutas de Gestión de Usuarios y Permisos
    path('usuarios/', include('usuarios.urls')),
    # Django Debug Toolbar
    path("__debug__/", include("debug_toolbar.urls")),
]


# Configuración para servir archivos de medios en entornos de desarrollo
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)