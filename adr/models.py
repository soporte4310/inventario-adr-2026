from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
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