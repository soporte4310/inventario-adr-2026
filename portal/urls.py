from django.urls import path
from .views import PortalIndexView

app_name = 'portal'

urlpatterns = [
    path('', PortalIndexView.as_view(), name='index'),
]