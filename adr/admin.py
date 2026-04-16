from django.contrib import admin
from .models import AllInOne, AllInOneAdmins, EquiposIsla, Notebook, MiniPC, Proyectores, Azotea, BodegaADR, Monitor, Audio, Tablet, SwitchDeRed, AreaAdministrativa, Cargo, Funcionario, Edificio, Piso, Ubicacion, Marca, Categoria, Catalogo, Estado, Activo, MapeoUbicacion

@admin.register(AllInOne)
class AllInOneAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'netbios', 'ubicacion', 'creado_por', 'fecha_creacion')

    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta
    
@admin.register(EquiposIsla)
class EquiposIslaAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'netbios', 'ubicacion', 'creado_por', 'fecha_creacion')

    @admin.display(description="Etiqueta", ordering="Etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta
    
@admin.register(SwitchDeRed)
class SwitchDeRedAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'netbios', 'ubicacion', 'creado_por', 'fecha_creacion')

    @admin.display(description="Etiqueta", ordering="Etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta


@admin.register(AllInOneAdmins)
class AllInOneAdminAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'netbios', 'ubicacion', 'creado_por', 'fecha_creacion')

    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta
        
@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'asignado_a', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'netbios', 'ubicacion', 'creado_por', 'fecha_creacion')

    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta

@admin.register(MiniPC)
class MiniPCAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'ubicacion', 'creado_por', 'fecha_creacion')
       
    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta

@admin.register(Proyectores)
class ProyectoresAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'ubicacion', 'creado_por', 'fecha_creacion')
      
@admin.register(Azotea)
class AzoteaAdmin(admin.ModelAdmin):
    list_display = ('activo', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'ubicacion', 'creado_por', 'fecha_creacion')
    
    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta
    
@admin.register(BodegaADR)
class BodegaADRAdmin(admin.ModelAdmin):
    list_display = ('activo', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'netbios', 'ubicacion', 'creado_por', 'fecha_creacion')
    
    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta
    
@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'ubicacion', 'creado_por', 'fecha_creacion')
    
    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta

@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'ubicacion', 'creado_por', 'fecha_creacion')
    
    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta
    
@admin.register(Tablet)
class TabletAdmin(admin.ModelAdmin):
    list_display = ('activo', 'estado', 'marca', 'modelo', 'n_serie', 'etiqueta', 'bdo', 'netbios', 'ubicacion', 'creado_por', 'fecha_creacion')
 
    @admin.display(description="Etiqueta", ordering="etiqueta")
    def etiqueta(self, obj):
        return obj.etiqueta
    

# NUEVOS MODELOS
class PisoInline(admin.TabularInline):
    model = Piso
    extra = 1

@admin.register(Edificio)
class EdificioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    inlines = [PisoInline]

@admin.register(Piso)
class PisoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edificio', 'descripcion')
    list_filter = ('edificio',)

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'piso', 'get_edificio')
    search_fields = ('nombre',)
    list_filter = ('piso__edificio', 'piso')

    def get_edificio(self, obj):
        return obj.piso.edificio
    get_edificio.short_description = 'Edificio'

# --- Configuración de Personal ---

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cargo', 'area', 'email', 'telefono')
    search_fields = ('nombre', 'email')
    list_filter = ('area', 'cargo')

# --- Configuración de Catálogo y Productos ---

@admin.register(Catalogo)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ('categoria', 'marca', 'modelo', 'created_at')
    list_filter = ('categoria', 'marca')
    search_fields = ('modelo', 'marca__nombre')

# --- El Modelo Principal: Activo ---

@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    # Columnas visibles en la lista
    list_display = (
        'etiqueta', 'bdo', 'catalogo', 'estado', 
        'ubicacion', 'asignado_a', 'tipo_red', 'is_deleted'
    )
    
    # Filtros laterales
    list_filter = (
        'is_deleted', 'estado', 'tipo_uso', 
        'tipo_red', 'catalogo__categoria', 'catalogo__marca'
    )
    
    # Buscador (muy importante para activos)
    search_fields = ('numero_serie', 'etiqueta', 'bdo', 'netbios', 'asignado_a__nombre')
    
    # Orden por defecto
    ordering = ('-created_at',)

    # Acciones personalizadas (Soft Delete)
    actions = ['restaurar_activos']

    def get_queryset(self, request):
        # Usamos all_objects para que el admin pueda ver los eliminados (is_deleted=True)
        return Activo.all_objects.all()

    @admin.action(description="Restaurar activos eliminados")
    def restaurar_activos(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, "Los activos seleccionados han sido restaurados.")


@admin.register(MapeoUbicacion)
class MapeoUbicacionAdmin(admin.ModelAdmin):
    # Solo texto plano y relaciones simples, sin widgets pesados
    list_display = ('nombre_original', 'ubicacion_nueva', 'revisado')
    
    # Filtro optimizado
    list_filter = ('revisado',)
    
    # Buscador simple
    search_fields = ('nombre_original',)
    
    # Evitamos que cargue miles de selects en los formularios de edición
    raw_id_fields = ('ubicacion_nueva',)
    
    # Desactivamos el conteo total de registros si la tabla es gigante (opcional)
    show_full_result_count = False

# --- Registros Simples ---

admin.site.register(AreaAdministrativa)
admin.site.register(Cargo)
admin.site.register(Marca)
admin.site.register(Categoria)
admin.site.register(Estado)