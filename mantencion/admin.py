from django.contrib import admin

from .models import CicloRevision, EquipoMantenible, EvidenciaRevision, Impresora, RevisionEquipo


@admin.register(Impresora)
class ImpresoraAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'nombre_equipo', 'ip', 'ubicacion', 'estado', 'creado_en')
    list_filter = ('estado', 'marca', 'modelo')
    search_fields = ('numero_serie', 'nombre_equipo', 'codigo_proveedor', 'ip')


@admin.register(EquipoMantenible)
class EquipoMantenibleAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tipo', 'activo_en_revision', 'agregado_por', 'fecha_agregado')
    list_filter = ('tipo', 'activo_en_revision')
    search_fields = ('activo__numero_serie', 'activo__etiqueta', 'impresora__numero_serie')


@admin.register(CicloRevision)
class CicloRevisionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tipo', 'fecha_inicio', 'fecha_generado', 'generado_por')
    list_filter = ('tipo',)


class EvidenciaRevisionInline(admin.TabularInline):
    model = EvidenciaRevision
    extra = 0
    readonly_fields = ('subido_por', 'subido_en')


@admin.register(RevisionEquipo)
class RevisionEquipoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'ciclo', 'estado', 'revisado_por', 'fecha_revision')
    list_filter = ('estado', 'ciclo')
    search_fields = ('equipo__activo__numero_serie', 'equipo__impresora__numero_serie', 'comentario')
    inlines = [EvidenciaRevisionInline]
