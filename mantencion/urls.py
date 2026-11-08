from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import inicio_mantencion


urlpatterns = [
    path('dashboard/', inicio_mantencion, name='inicio_mantencion'),

]
