from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class AreaAdministrativa(models.Model):
    """Modelo para registrar áreas administrativas o departamentos dentro de la sede"""
    nombre = models.CharField(verbose_name="Nombre", max_length=100)
    sigla = models.CharField(verbose_name="Sigla", max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "Área Administrativa"
        verbose_name_plural = "Áreas Administrativas"

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
    
    def clean(self):
        super().clean()
        # Normalización: quita espacios y convierte a mayúsculas
        if self.nombre:
            self.nombre = self.nombre.strip().upper()


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
    
    def clean(self):
        super().clean()
        # Normalización: quita espacios y convierte a mayúsculas
        if self.nombre:
            self.nombre = self.nombre.strip().upper()


class Categoria(models.Model):
    """Modelo para registrar las diferentes categorías o tipos de producto"""
    nombre = models.CharField(verbose_name="Nombre", max_length=100, help_text="Ingrese el nombre de la categoría (tipo). Ej: Televisor, All in One, Monitor, Laptop, etc.")
    descripcion = models.TextField(verbose_name="Descripción (opcional)", null=True, blank=True)
    usa_netbios = models.BooleanField(default=False, verbose_name="¿Requiere NetBIOS?", help_text="Marque si los equipos de esta categoría se unen al dominio.")
    usa_bdo = models.BooleanField(default=True, verbose_name="¿Requiere BDO?", help_text="Marque si a estos equipos se les pega placa de inventario.")
    imagen = models.ImageField(verbose_name="Imagen representativa", null=True, blank=True, upload_to="categorias/imagen/main")
    imagen_thumb_medium = models.ImageField(verbose_name="Thumbnail (600x600)", upload_to="categorias/imagen/medium/", blank=True, null=True, editable=False)
    imagen_thumb_small = models.ImageField(verbose_name="Thumbnail (50x50)", upload_to="categorias/imagen/small/", blank=True, null=True, editable=False)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre
    
    def clean(self):
        super().clean()
        # Normalización: quita espacios y convierte a mayúsculas
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
    
#    def clean(self):
#        super().clean()
#        
#        # Solo verificamos si la categoría ya existía (es una edición, no una creación)
#        if self.pk:
#            categoria_antigua = Categoria.objects.get(pk=self.pk)
#            
#            cambio_netbios = self.usa_netbios != categoria_antigua.usa_netbios
#            cambio_bdo = self.usa_bdo != categoria_antigua.usa_bdo
#
#            # Si intentan cambiar los checks, verificamos si hay activos
#            if cambio_netbios or cambio_bdo:
#                # Importamos Activo aquí adentro para evitar un error de "importación circular" en Django
#                from adr.models import Activo 
#                
#                # Buscamos si hay activos que pertenezcan a algún catálogo de esta categoría
#                tiene_activos = Activo.objects.filter(catalogo__categoria=self).exists()
#                
#                if tiene_activos:
#                    raise ValidationError(
#                        "No puedes modificar las reglas de NetBIOS o BDO porque ya existen equipos físicos registrados bajo esta categoría."
#                    )


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
        verbose_name = "Catálogo de producto"
        verbose_name_plural = "Catálogo de productos"

        # Combinación de categoría, marca y modelo debe ser única para evitar duplicados
        constraints = [
            models.UniqueConstraint(
                fields=['categoria', 'marca', 'modelo'], 
                name='unique_catalogo_producto'
            )
        ]

    def __str__(self):
        return f"{self.categoria} {self.marca.nombre} {self.modelo}"
    
    def clean(self):
        super().clean()
        # Normalización: quita espacios, convierte a mayúsculas y limpia variantes de modelos génericos
        if self.modelo:
            modelo_limpio = self.modelo.strip().upper()

            textos_genericos = [
                'GENÉRICO', 'GENERICO', 'MOD. GENÉRICO', 'MOD. GENERICO',
                'MOD GENÉRICO', 'MOD GENERICO', 'SIN MODELO', 'S/M', 'NO APLICA', 'N/A'
            ]
            
            if modelo_limpio in textos_genericos:
                self.modelo = "GENÉRICO"
            else:
                self.modelo = modelo_limpio


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
    """Manager personalizado creado para el Modelo Activo, el cual filtra los equipos eliminados en el queryset por defecto, facilitando así la implementación de un soft delete.

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
        ACADEMICO = 'ACA', 'Académico'
        ADMINISTRATIVO = 'ADM', 'Administrativo'
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
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, verbose_name="Ubicación", help_text="Seleccionar ubicación donde se encuentra el equipo", null=True, blank=True)
    asignado_a = models.ForeignKey(Funcionario, on_delete=models.PROTECT, verbose_name="Asignatario", help_text="Seleccionar persona responsable del equipo", null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, verbose_name="Registrado por", null=True, blank=True)
    is_deleted = models.BooleanField(default=False, verbose_name="Eliminado")
    acta_entrega = models.FileField(upload_to='documentos/actas/entregas/', validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Acta de Entrega", help_text="Suba el acta de entrega escaneada en formato PDF", null=True, blank=True)
    acta_devolucion = models.FileField(upload_to='documentos/actas/devoluciones/', validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Acta de Devolución", help_text="Suba el acta de devolución escaneada en formato PDF", null=True, blank=True)
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
            models.UniqueConstraint(
                fields=['numero_serie'], 
                condition=Q(is_deleted=False, numero_serie__isnull=False), 
                name='unique_nserie_activos'
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

        # 1. NORMALIZACIÓN INTELIGENTE DEL BDO
        if self.bdo in [None, '', '0', ' ']:
            self.bdo = None
        else:
            # Quitamos espacios en blanco
            bdo_limpio = str(self.bdo).strip()
            
            # Validamos que solo contenga números
            if not bdo_limpio.isdigit():
                raise ValidationError({'bdo': 'El código BDO debe contener únicamente números.'})

            # Si el código NO tiene 12 dígitos, o NO empieza con '26', 
            # asumimos que el técnico lo escribió a mano en su versión corta.
            if len(bdo_limpio) != 12 or not bdo_limpio.startswith('26'):
                # bdo_limpio.zfill(10) convierte "11180" en "0000011180"
                # Luego le pegamos el "26" al inicio.
                self.bdo = f"26{bdo_limpio.zfill(10)}"
            else:
                # Si ya tiene 12 dígitos y empieza con 26 (ej: escaneado con pistola láser)
                self.bdo = bdo_limpio

        # 2. NORMALIZACIÓN DE ETIQUETA
        if self.etiqueta in [None, '', '0', ' ']:
            self.etiqueta = None
        else:
            self.etiqueta = str(self.etiqueta).strip()

        # 3. NORMALIZACIÓN DE NÚMERO DE SERIE
        # Si envían vacío, ceros, o textos genéricos de "No Aplica", lo hacemos NULL
        if str(self.numero_serie).strip().upper() in ['NONE', '', '0', 'N/A', 'S/N', 'NO TIENE']:
            self.numero_serie = None
        else:
            self.numero_serie = str(self.numero_serie).strip()

        # 4. VALIDACIÓN DE COLISIONES (FORMULARIOS AMIGABLES)
        # Revisamos si el código ya existe en un equipo ACTIVO para no lanzar error 500
        qs_activos = Activo.objects.filter(is_deleted=False).exclude(pk=self.pk)

        if self.bdo and qs_activos.filter(bdo=self.bdo).exists():
            raise ValidationError({'bdo': f"El BDO {self.bdo} ya está en uso por un equipo activo."})

        if self.etiqueta and qs_activos.filter(etiqueta=self.etiqueta).exists():
            raise ValidationError({'etiqueta': f"La etiqueta {self.etiqueta} ya está registrada en un equipo activo."})
        
        if self.numero_serie and qs_activos.filter(numero_serie=self.numero_serie).exists():
            raise ValidationError({'numero_serie': f"El Número de Serie '{self.numero_serie}' ya está registrado en otro equipo del inventario."})
        
        # 5. VALIDACIÓN DINÁMICA GUIADA POR LA CATEGORÍA (Se desactiva esta restricción para hacer al sistema más flexible)
        #if self.catalogo and self.catalogo.categoria:
        #    categoria = self.catalogo.categoria
        #
        #    # Validación de NetBIOS
        #    if categoria.usa_netbios:
        #        if self.tipo_red == self.TipoRed.DOMINIO and not self.netbios:
        #            raise ValidationError({'netbios': f"Los equipos de la categoría '{categoria.nombre}' conectados al dominio deben tener un código NetBIOS."})
        #    else:
        #        if self.netbios:
        #            raise ValidationError({'netbios': f"La categoría '{categoria.nombre}' no requiere NetBIOS. Deje este campo en blanco."})
        #
        #    # Validación de BDO
        #    if not categoria.usa_bdo:
        #        if self.bdo:
        #            raise ValidationError({'bdo': f"La categoría '{categoria.nombre}' no requiere placa BDO. Deje este campo en blanco."})

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




class AuditoriaActivo(models.Model):
    class TipoAccion(models.TextChoices):
        CREACION = 'CRE', 'Creación'
        MODIFICACION = 'MOD', 'Modificación'
        ELIMINACION = 'ELI', 'Eliminación'
        RESTAURACION = 'RES', 'Restauración'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Técnico Responsable"
    )
    accion = models.CharField(max_length=3, choices=TipoAccion.choices, verbose_name="Acción Realizada")
    
    # Enlace genérico para auditar Activos, Ubicaciones o Funcionarios
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Detalles del cambio
    campo = models.CharField(max_length=100, verbose_name="Campo Editado", null=True, blank=True)
    valor_anterior = models.TextField(verbose_name="Valor Anterior", null=True, blank=True)
    valor_nuevo = models.TextField(verbose_name="Valor Nuevo", null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")

    class Meta:
        verbose_name = "Auditoría de Inventario"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_accion_display()} por {self.usuario} - {self.fecha.strftime('%d/%m/%Y')}"