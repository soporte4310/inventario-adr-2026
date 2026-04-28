
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")), # RECARGA LA PAGINA EN TIEMPO REAL CUANDO SE REALIZAN CAMBIOS
    path("accounts/", include("accounts.urls")), # RUTAS DE AUTENTICACIÓN (login personalizado)
    # Para otras funcionalidades de auth (logout, password reset, etc.) que no estén en accounts.urls:
    # path("accounts/", include("django.contrib.auth.urls")), # Asegúrate de que no haya conflictos de nombres
    # path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('', include('adr.urls')),
    
    # Rutas nuevas para el inventario
    path('inventario/', include('inventario.urls')),
]


# Configuración para servir archivos de medios en entornos de desarrollo
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)