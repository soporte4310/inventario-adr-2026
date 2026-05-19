from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
    AddUserView, ProfileListView, ProfileUpdateView, ProfileDeleteView, PrestamoListView, AddPrestamoView, DevolverPrestamoView
)

from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import UserPasswordChangeView


urlpatterns = [
    # Gestión de Usuarios
    path('add_user/', login_required(AddUserView.as_view()), name="add_user"),
    path('profile_edit/<int:pk>/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
    path('profile_list/', login_required(ProfileListView.as_view()), name="profile_list"),
    path("mi-perfil/", views.my_profile, name="my_profile"),
    path('profile_delete/<int:pk>/', login_required(ProfileDeleteView.as_view()), name='profile_delete'),
    path("perfil/contraseña/cambiar/", UserPasswordChangeView.as_view(), name="password_change"),

    # Gestión de Préstamos
    path('prestamos/', login_required(PrestamoListView.as_view()), name='prestamos'),
    path('add_prestamo/', login_required(AddPrestamoView.as_view()), name='add_prestamo'),
    path('prestamo/<int:pk>/devolver/', login_required(DevolverPrestamoView.as_view()), name='devolver_prestamo'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)