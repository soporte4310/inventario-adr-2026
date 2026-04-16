from django.db import models
from django.urls import reverse
from django.conf import settings
from accounts.models import Profile
from django.core.exceptions import ValidationError
from django.db.models import Q
from .opciones import (
    opciones_sala_All_In_One, opciones_estado, opciones_marca_all_in_one,
    opciones_ubicacion_all_in_one_admin, opciones_marca_notebook,
    opciones_ubicacion_notebook, opciones_marca_mini_pc, opciones_ubicacion_mini_pc,
    opciones_marca_proyector, opciones_ubicacion_proyector, opciones_activos,
    opciones_marca_azotea, opciones_estado_activo,
    opciones_edificio, opciones_marca_monitor, opciones_ubicacion_monitor,
    opciones_marca_audio, opciones_ubicacion_audio 
)

class ActivoBase(models.Model):
    """Modelo base para todos los activos. No incluye unique en n_serie para permitir duplicados históricos"""
    activo = models.CharField(max_length=150, verbose_name='Activo')
    modelo = models.CharField(max_length=100, verbose_name='Modelo')
    # Removido unique=True para permitir duplicados históricos
    n_serie = models.CharField(max_length=100, verbose_name='Número Serie', blank=True, null=True)
    etiqueta = models.CharField(max_length=100, verbose_name='Etiqueta', blank=True, null=True)
    bdo = models.DecimalField(max_digits=30, decimal_places=0, verbose_name='BDO', null=True, blank=True, default=0)
    estado = models.CharField(max_length=100, default='Activo', verbose_name='Estado', blank=True, null=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_created', verbose_name='Registrador por')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Fecha de Última Modificación')  # Nueva columna


    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.marca} {self.modelo} {self.n_serie}'

class EquipoInformatico(ActivoBase):
    """Modelo base para equipos informáticos"""
    netbios = models.CharField(max_length=100, verbose_name='NetBios', default='', blank=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()

        etiqueta = str(self.etiqueta).strip() if self.etiqueta not in [None, ''] else '0'
        bdo = str(self.bdo).strip() if self.bdo not in [None, ''] else '0'

        if etiqueta == '0' and bdo == '0':
            return

        model_class = self.__class__
        qs = model_class.objects.exclude(pk=self.pk)

        if bdo != '0' and qs.filter(bdo=bdo).exists():
            raise ValidationError({'bdo': "Este código BDO ya está registrado."})

        if etiqueta != '0' and qs.filter(etiqueta=etiqueta).exists():
            raise ValidationError({'etiqueta': "Este código Etiqueta ya está registrado."})

        if etiqueta == '0' and bdo != '0' and qs.filter(bdo=bdo).exists():
            raise ValidationError({'bdo': "Este BDO ya está registrado y el Etiqueta es 0. No se permite."})

        if bdo == '0' and etiqueta != '0' and qs.filter(etiqueta=etiqueta).exists():
            raise ValidationError({'etiqueta': "Este Etiqueta ya está registrado y el BDO es 0. No se permite."})

    # Si ambos son 0, permitir sin restricciones
    def save(self, *args, **kwargs):
            self.full_clean()  # Ejecuta validación antes de guardar
            super().save(*args, **kwargs)

class MiniPC(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Mini PC'
        verbose_name_plural = 'Mini PCs'
        ordering = ['ubicacion', '-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_minipc', kwargs={'pk': self.pk})

class AllInOne(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'All In One Académico'
        verbose_name_plural = 'All In Ones Académicos'
        ordering = ['ubicacion', '-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_allinone', kwargs={'pk': self.pk})
    
    
class SwitchDeRed(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Switch De Red'
        verbose_name_plural = 'Switches De Redes'
        ordering = ['ubicacion', '-fecha_creacion']
        indexes = [ models.Index(fields=['creado_por'], name='idx_switchdered_creado_por'),]

    def get_absolute_url(self):
        return reverse('detalle_switchdered', kwargs={'pk': self.pk})



class AllInOneAdmins(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'All In One Administrativo'
        verbose_name_plural = 'All In Ones Administrativos'
        ordering = ['ubicacion', '-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_allinone_admin', kwargs={'pk': self.pk})

class Notebook(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    asignado_a = models.CharField(max_length=150, verbose_name='Asignado a')
    ubicacion = models.CharField(max_length=150, default='Seleccione', verbose_name='Ubicación')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Notebook'
        verbose_name_plural = 'Notebooks'
        ordering = ['ubicacion', '-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_notebook', kwargs={'pk': self.pk})

class Proyectores(ActivoBase):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Edificio')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Proyector'
        verbose_name_plural = 'Proyectores'
        ordering = ['ubicacion', '-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_proyector', kwargs={'pk': self.pk})

class BodegaADR(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='', verbose_name='Ubicación') # Renombrado de estado_activo a ubicacion y eliminado choices
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Equipo en Bodega ADR'
        verbose_name_plural = 'Equipos en Bodega ADR'
        ordering = ['-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_bodegaadr', kwargs={'pk': self.pk})

class Azotea(ActivoBase):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='', verbose_name='Ubicación', blank=True, null=True)
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Equipo en Azotea'
        verbose_name_plural = 'Equipos en Azotea'
        ordering = ['-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_azotea', kwargs={'pk': self.pk})

class Monitor(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación') # Eliminado choices=opciones_ubicacion_monitor
    asignado_a = models.CharField(max_length=150, verbose_name='Asignado a', blank=True, null=True) # Nuevo campo

    class Meta:
        verbose_name = 'Monitor'
        verbose_name_plural = 'Monitores'
        ordering = ['ubicacion', '-fecha_creacion']
 
    def get_absolute_url(self):
        return reverse('detalle_monitor', kwargs={'pk': self.pk}) # TODO: Crear URL 'detalle_monitor'
 
class Audio(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    modelo = models.CharField(max_length=100, verbose_name='Modelo', null=True, blank=True) # Hacer el campo modelo opcional
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación')

    class Meta:
        verbose_name = 'Equipo de Audio'
        verbose_name_plural = 'Equipos de Audio'
        ordering = ['ubicacion', '-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_audio', kwargs={'pk': self.pk}) # TODO: Crear URL 'detalle_audio'

class Tablet(EquipoInformatico):
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=255, default='Seleccione', verbose_name='Ubicación')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Tablet'
        verbose_name_plural = 'Tablets'
        ordering = ['ubicacion', '-fecha_creacion']

    def get_absolute_url(self):
        return reverse('detalle_tablet', kwargs={'pk': self.pk}) # TODO: Crear URL 'detalle_tablet'


####
class EquiposIsla(EquipoInformatico):
    # fijo el tipo por defecto (opcional)
    activo = models.CharField(max_length=150, default='Equipos Isla', verbose_name='Activo')

    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación')
    netbios = models.CharField(max_length=100, verbose_name='NetBIOS', null=True, blank=True)

    class Meta:
        verbose_name = 'Equipo Isla'
        verbose_name_plural = 'Equipos Islas'
        ordering = ['ubicacion', '-fecha_creacion']
        indexes = [
            models.Index(fields=['creado_por'], name='idx_equiposisla_creado_por'),
        ]

    def get_absolute_url(self):
        return reverse('detalle_equiposisla', kwargs={'pk': self.pk})


class Eliminados(models.Model):
    """Modelo para guardar registros que han sido eliminados de las tablas originales."""
    activo = models.CharField(max_length=150, verbose_name='Activo', null=True, blank=True)
    modelo = models.CharField(max_length=100, verbose_name='Modelo', null=True, blank=True)
    n_serie = models.CharField(max_length=100, verbose_name='Número Serie', null=True, blank=True)
    etiqueta = models.CharField(max_length=100, verbose_name='Etiqueta', null=True, blank=True)
    bdo = models.DecimalField(max_digits=30, decimal_places=0, verbose_name='BDO', null=True, blank=True)
    estado = models.CharField(max_length=100, verbose_name='Estado', null=True, blank=True)
    marca = models.CharField(max_length=100, verbose_name='Marca', null=True, blank=True)
    netbios = models.CharField(max_length=100, verbose_name='NetBios', default='', blank=True, null=True)
    ubicacion = models.CharField(max_length=150, verbose_name='Ubicación', null=True, blank=True)
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Eliminado por'
    )
    fecha_eliminacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Eliminación')

    class Meta:
        verbose_name = 'Registro Eliminado'
        verbose_name_plural = 'Registros Eliminados'
        ordering = ['-fecha_eliminacion']

    def __str__(self):
        return f'Eliminado: {self.activo} - {self.modelo} - {self.n_serie}'


class HistorialCambios(models.Model):
    modelo = models.CharField(max_length=100, verbose_name='Modelo Modificado')
    objeto_id = models.IntegerField(verbose_name='ID del Objeto Modificado', null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Usuario que Modificó'
    )
    campo_modificado = models.CharField(max_length=100, verbose_name='Campo Modificado')
    valor_anterior = models.TextField(verbose_name='Valor Anterior')
    valor_nuevo = models.TextField(verbose_name='Valor Nuevo')
    fecha_modificacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Modificación')

    class Meta:
        verbose_name = 'Historial de Cambios'
        verbose_name_plural = 'Historial de Cambios'
        ordering = ['-fecha_modificacion']


class Televisor(ActivoBase):
    """Modelo para Televisores"""
    marca = models.CharField(max_length=100, default='', verbose_name='Marca')
    ubicacion = models.CharField(max_length=100, default='Seleccione', verbose_name='Ubicación')

    class Meta:
        verbose_name = 'Televisor'
        verbose_name_plural = 'Televisores'
        ordering = ['ubicacion', '-fecha_creacion']
        indexes = [models.Index(fields=['creado_por'], name='idx_televisor_creado_por'),]

    def get_absolute_url(self):
        return reverse('detalle_televisor', kwargs={'pk': self.pk})


#--------------------------------------------------------------
# NUEVOS MODELOS
#--------------------------------------------------------------
class AreaAdministrativa(models.Model):
    """Modelo para registrar áreas administrativas o departamentos dentro de la sede"""
    nombre = models.CharField(verbose_name="Nombre", max_length=100)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    """Modelo para registrar los cargos de los funcionarios"""
    nombre = models.CharField(verbose_name="Nombre", max_length=100)
    es_adr = models.BooleanField(verbose_name="Es cargo de ADR", default=False, help_text="Seleccione si el cargo es exclusivo de ADR")

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"

    def __str__(self):
        return self.nombre


class Funcionario(models.Model):
    """Modelo para registrar a las personas a las que se les asigna equipos (Administrativos, Docentes, etc.)."""
    nombre = models.CharField(verbose_name="Nombre", max_length=100)
    telefono = models.CharField(verbose_name="Teléfono", max_length=20, blank=True, null=True)
    email = models.EmailField(verbose_name="Email", max_length=100, blank=True, null=True)
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, verbose_name="Cargo", null=True, blank=True)
    area = models.ForeignKey(AreaAdministrativa, on_delete=models.PROTECT, verbose_name="Área administrativa", null=True, blank=True)

    class Meta:
        verbose_name = "Funcionario"
        verbose_name_plural = "Funcionarios"

    def __str__(self):
        return self.nombre


class Edificio(models.Model):
    """Modelo para registrar los edificios disponibles en la sede"""
    nombre = models.CharField(verbose_name="Nombre", unique=True, max_length=50, help_text="Ingrese el nombre del Edificio")
    descripcion = models.TextField(verbose_name="Descripción (opcional)", null=True, blank=True)

    class Meta:
        verbose_name = "Edificio"
        verbose_name_plural = "Edificios"

    def __str__(self):
        return self.nombre


class Piso(models.Model):
    """Modelo para registrar los niveles/pisos disponibles en los edificios"""
    nombre = models.CharField(verbose_name="Piso", max_length=20, help_text="Ingrese el nombre del Piso/Nivel")
    descripcion = models.TextField(verbose_name="Descripción (opcional)", null=True, blank=True)
    edificio = models.ForeignKey(Edificio, on_delete=models.PROTECT, verbose_name="Edificio", help_text="Seleccione el edificio correspondiente")

    class Meta:
        verbose_name = "Piso"
        verbose_name_plural = "Pisos"

    def __str__(self):
        return f'{self.edificio}, {self.nombre}'


class Ubicacion(models.Model):
    """Modelo para registrar la ubicación final de los equipos. Estas pueden ser, salas, pasillos, bodegas, etc."""
    nombre = models.CharField(verbose_name="Ubicación", max_length=100, help_text="Ingrese de la ubicación (sala, bodega, pasillo, etc.)")
    descripcion = models.TextField(verbose_name="Descripción (opcional)", null=True, blank=True)
    imagen = models.ImageField(verbose_name="Imagen de la ubicación", null=True, blank=True, upload_to="ubicaciones/imagen/main")
    imagen_thumb_medium = models.ImageField(verbose_name="Thumbnail (600x600)", upload_to="ubicaciones/imagen/medium/", blank=True, null=True,editable=False)
    imagen_thumb_small = models.ImageField(verbose_name="Thumbnail (50x50)",upload_to="ubicaciones/imagen/small/", blank=True, null=True,editable=False)
    piso = models.ForeignKey(Piso, on_delete=models.PROTECT, verbose_name="Piso", help_text="Seleccione el piso/nivel correspondiente")

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"

    def __str__(self):
        return f'{self.piso}, {self.nombre}'


class Marca(models.Model):
    """Modelo para registrar marcas de productos"""
    nombre = models.CharField(verbose_name="Nombre", unique=True, max_length=50, help_text="Ingrese el nombre de la marca")

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    """Modelo para registrar las diferentes categorías o tipos de producto"""
    nombre = models.CharField(verbose_name="Nombre", max_length=100, help_text="Ingrese el nombre de la categoría (tipo). Ej: Televisor, All in One, Monitor, Laptop, etc.")
    descripcion = models.TextField(verbose_name="Descripción (opcional)", null=True, blank=True)
    usa_netbios = models.BooleanField(default=False, verbose_name="¿Requiere NetBIOS?", help_text="Marque si los equipos de esta categoría se unen al dominio.")
    usa_bdo = models.BooleanField(default=True, verbose_name="¿Requiere BDO?", help_text="Marque si a estos equipos se les pega placa de inventario.")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre
    
    def clean(self):
        super().clean()
        
        # Solo verificamos si la categoría ya existía (es una edición, no una creación)
        if self.pk:
            categoria_antigua = Categoria.objects.get(pk=self.pk)
            
            cambio_netbios = self.usa_netbios != categoria_antigua.usa_netbios
            cambio_bdo = self.usa_bdo != categoria_antigua.usa_bdo

            # Si intentan cambiar los checks, verificamos si hay activos
            if cambio_netbios or cambio_bdo:
                # Importamos Activo aquí adentro para evitar un error de "importación circular" en Django
                from adr.models import Activo 
                
                # Buscamos si hay activos que pertenezcan a algún catálogo de esta categoría
                tiene_activos = Activo.objects.filter(catalogo__categoria=self).exists()
                
                if tiene_activos:
                    raise ValidationError(
                        "No puedes modificar las reglas de NetBIOS o BDO porque ya existen equipos físicos registrados bajo esta categoría."
                    )


class Catalogo(models.Model):
    """Modelo para crear productos. Los productos creados aquí servirán para registrar activos o equipos reales en el modelo para activos"""
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name="Categoría (tipo)", help_text="Seleccione la categoría correspondiente")
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, verbose_name="Marca", help_text="Seleccione la marca correspondiente")
    modelo = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField(verbose_name="Detalle (opcional)", null=True, blank=True)
    imagen = models.ImageField(verbose_name="Imagen (opcional)", upload_to="productos/imagen/main/", blank=True, null=True)
    imagen_thumb_medium = models.ImageField(verbose_name="Thumbnail (600x600)", upload_to="productos/imagen/medium/", blank=True, null=True,editable=False)
    imagen_thumb_small = models.ImageField(verbose_name="Thumbnail (50x50)",upload_to="productos/imagen/small/", blank=True, null=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.categoria} {self.marca.nombre} {self.modelo}"


class Estado(models.Model):
    '''Modelo para registrar los diferentes estados que pueden tener los equipos'''
    nombre = models.CharField(verbose_name="Nombre", unique=True, max_length=50, help_text="Ingrese el nombre del estado")
    descripcion = models.TextField(verbose_name="Descripción (opcional)", null=True, blank=True)

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"

    def __str__(self):
        return self.nombre
    

class ActivoManager(models.Manager):
    """Manager personalizado creado para el Modelo Activo, el cual filtra los equipos eliminados en el queryset por defecto, permitiendo así la implementación de un soft delete.

    La columna 'is_deleted' en el modelo 'Activo' busca reemplazar la complejidad del modelo 'Eliminados'.
    """
    def get_queryset(self):
        # Por defecto, este manager SIEMPRE filtra y oculta los eliminados
        return super().get_queryset().filter(is_deleted=False)


class Activo(models.Model):
    """Modelo para registrar equipos reales"""

    class TipoUso(models.TextChoices):
        PERSONAL = 'PER', 'Personal/Oficina'
        LABORATORIO = 'LAB', 'Laboratorio/Sala'
        EVENTOS = 'EVE', 'Eventos'
        OTRO = 'OTR', 'Otro'

    class TipoRed(models.TextChoices):
        DOMINIO = 'DOM', 'Red Institucional (Dominio)'
        ISLA = 'ISLA', 'Equipo Isla'
        LAB = 'LAB', 'Laboratorio Aislado'
        OTRO = 'OTRO', 'Otro / Sin Red'

    catalogo = models.ForeignKey(Catalogo, on_delete=models.PROTECT, verbose_name="Catálogo", help_text="Seleccione el producto correspondiente")
    numero_serie = models.CharField(verbose_name="N° de serie", max_length=50, help_text="Ingrese el número de serie del equipo", null=True, blank=True)
    etiqueta = models.CharField(verbose_name="Etiqueta", max_length=50, help_text="Ingrese el código de la etiqueta del equipo", null=True, blank=True)
    bdo = models.CharField(verbose_name="Número BDO", max_length=50, help_text="Ingrese el número BDO del equipo", null=True, blank=True)
    netbios = models.CharField(verbose_name="Código NetBios", max_length=50, help_text="Ingrese el código NetBios del equipo", null=True, blank=True)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, verbose_name="Estado", help_text="Seleccione el estado correspondiente")
    tipo_uso = models.CharField(max_length=3, choices=TipoUso.choices, default=TipoUso.PERSONAL, verbose_name="Propósito / Tipo de Uso", help_text="Define si el equipo es de uso regular, de laboratorio o reservado para eventos")
    tipo_red = models.CharField(max_length=4, choices=TipoRed.choices, default=TipoRed.DOMINIO, verbose_name='Tipo de Conexión/Red')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, verbose_name="Ubicación", help_text="Seleccionar ubicación donde se encuentra el equipo")
    asignado_a = models.ForeignKey(Funcionario, on_delete=models.PROTECT, verbose_name="Asignatario", help_text="Seleccionar persona responsable del equipo", null=True, blank=True)
    is_deleted = models.BooleanField(default=False, verbose_name="Eliminado")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActivoManager() # El manager principal ahora oculta los eliminados
    all_objects = models.Manager() # Manager secundario para ver TODO (ej: panel de admin)

    class Meta:
        verbose_name = "Activo"
        verbose_name_plural = "Activos"

        # Los códigos deben ser únicos, 
        # pero solo entre los equipos que no están eliminados".
        constraints = [
            models.UniqueConstraint(
                fields=['bdo'], 
                condition=Q(is_deleted=False, bdo__isnull=False), 
                name='unique_bdo_activos'
            ),
            models.UniqueConstraint(
                fields=['etiqueta'], 
                condition=Q(is_deleted=False, etiqueta__isnull=False), 
                name='unique_etiqueta_activos'
            ),
        ]

        default_permissions = []

        permissions = [
            ("view_activo", "Ver activos del sistema"),
            ("add_activo", "Agregar nuevos activos"),
            ("change_activo", "Modificar información de los activos"),
            ("deactivate_activo", "Dar de baja activos (Cambiar estado)"),
            ("delete_activo", "Eliminar activos"),
        ]

    def __str__(self):
        return f'{self.catalogo} - {self.numero_serie or self.etiqueta}'
    
    def clean(self):
        super().clean()
        
        # Si envían un campo vacío, un espacio en blanco o el viejo '0', 
        # se transforma en un verdadero valor Nulo para la base de datos.
        if self.bdo in [None, '', '0', ' ']:
            self.bdo = None
        else:
            self.bdo = str(self.bdo).strip()

        if self.etiqueta in [None, '', '0', ' ']:
            self.etiqueta = None
        else:
            self.etiqueta = str(self.etiqueta).strip()

        # 2. VALIDACIÓN PARA FORMULARIOS AMIGABLES:
        # En lugar de dejar que la base de datos lance un error 500, 
        # revisamos si el código ya existe en un equipo ACTIVO y mostramos un mensaje amigable.
        qs_activos = Activo.objects.filter(is_deleted=False).exclude(pk=self.pk)

        if self.bdo and qs_activos.filter(bdo=self.bdo).exists():
            raise ValidationError({'bdo': f"El BDO {self.bdo} ya está en uso por un equipo activo."})

        if self.etiqueta and qs_activos.filter(etiqueta=self.etiqueta).exists():
            raise ValidationError({'etiqueta': f"La etiqueta {self.etiqueta} ya está registrada en un equipo activo."})
        

        # Validación dinámica guiada por la categoría
        if self.catalogo and self.catalogo.categoria:
            categoria = self.catalogo.categoria

            # 1. Validación de NetBIOS
            if categoria.usa_netbios:
                if self.tipo_red == self.TipoRed.DOMINIO and not self.netbios:
                    raise ValidationError({'netbios': f"Los equipos de la categoría '{categoria.nombre}' conectados al dominio deben tener un código NetBIOS."})
            else:
                # Si la categoría no usa NetBIOS, forzamos la limpieza por si el usuario lo llenó por error
                self.netbios = None

            # 2. Validación de BDO
            if categoria.usa_bdo and not self.bdo:
                # Opcional: Lanzar error si es obligatorio el primer día, 
                # Dejar pasar si permiten guardar sin BDO temporalmente.
                pass
            elif not categoria.usa_bdo:
                # Si es un cable o algo menor que no usa BDO, lo limpiamos
                self.bdo = None

    def save(self, *args, **kwargs):
        self.full_clean() # Ejecuta el clean() automáticamente antes de guardar
        super().save(*args, **kwargs)
    
    def delete(self, user=None, *args, **kwargs):
        """
        En lugar de borrar el registro de la BD, lo marca como eliminado.
        """
        self.is_deleted = True
        self.save()


class MapeoUbicacion(models.Model):
    """
    Tabla intermedia para limpiar ubicaciones durante el proceso ETL.
    Conecta el string sucio de las tablas viejas con el modelo Ubicacion nuevo.
    """
    nombre_original = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name="Ubicación Original (Texto Sucio)"
    )
    ubicacion_nueva = models.ForeignKey(
        'Ubicacion', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Ubicación Estandarizada",
        help_text="Seleccione la ubicación real a la que corresponde el texto original."
    )
    revisado = models.BooleanField(
        default=False, 
        verbose_name="Validado por humano"
    )

    class Meta:
        verbose_name = "Mapeo de Ubicación"
        verbose_name_plural = "Mapeos de Ubicaciones"

    def __str__(self):
        estado = "✅" if self.revisado else "❌"
        return f"{estado} {self.nombre_original} -> {self.ubicacion_nueva or 'Pendiente'}"