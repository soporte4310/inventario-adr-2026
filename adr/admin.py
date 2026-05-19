from django.contrib import admin
from .models import Prestamo
    
@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('item_prestado', 'docente_nombre', 'sala', 'estado', 'fecha_prestamo')
    list_filter = ('estado', 'item_prestado', 'fecha_prestamo')
    search_fields = ('docente_nombre', 'docente_rut', 'sala', 'item_prestado')
    readonly_fields = ('fecha_prestamo',)