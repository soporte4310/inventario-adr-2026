from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from inventario.models import Activo, Ubicacion


class Impresora(models.Model):
    """
    Una impresora administrada por un proveedor externo (hoy Sonda, podría
    cambiar), por lo que NO es un Activo de inventario: INACAP no es dueño
    del equipo, así que se modela aparte, sin ninguna FK a Activo/Catalogo/
    Marca de 'inventario'. Sí reutiliza Ubicacion y Estado, porque esos son
    catálogos de referencia compartidos (salas/edificios, "Operativo"/"De
    Baja"), no datos de propiedad de un activo específico.
    """

    class EstadoImpresora(models.TextChoices):
        OPERATIVA = 'OPER', 'Operativa'
        DE_BAJA = 'BAJA', 'De Baja / Deprecada'

    marca = models.CharField(max_length=50, default='HP', verbose_name="Marca")
    modelo = models.CharField(max_length=50, verbose_name="Modelo")
    tipo_impresion = models.CharField(
        max_length=30, blank=True, verbose_name="Tipo de impresión",
        help_text="Ej: Blanco y Negro, Color"
    )
    rango_impresiones = models.CharField(
        max_length=30, blank=True, verbose_name="Rango de impresiones contratado"
    )
    nombre_equipo = models.CharField(
        max_length=100, blank=True, verbose_name="Nombre de red",
        help_text="Hostname asignado por el proveedor, ej: IQQ_E540_BODEGA"
    )
    numero_serie = models.CharField(max_length=50, unique=True, verbose_name="N° de Serie")
    ip = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True, verbose_name="IP")
    mac = models.CharField(max_length=17, blank=True, verbose_name="MAC")
    codigo_proveedor = models.CharField(
        # No es unique: en la práctica el proveedor a veces repite este
        # código entre equipos distintos (ej: por contrato/lote). El N° de
        # Serie es el identificador confiable, ese sí es único.
        max_length=30, blank=True, null=True, verbose_name="Código del proveedor"
    )
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name='+'
    )
    estado = models.CharField(
        max_length=4, choices=EstadoImpresora.choices, default=EstadoImpresora.OPERATIVA,
        verbose_name="Estado"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Agregada por"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Impresora"
        verbose_name_plural = "Impresoras"
        ordering = ['modelo', 'nombre_equipo']

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.numero_serie}"


class EquipoMantenible(models.Model):
    """
    Enlaza un equipo (proyector O impresora) al circuito de mantención.

    Los proyectores YA están inventariados en 'inventario' (Activo es la
    única fuente de verdad para ellos); las impresoras NO son activos de
    inventario (las entrega un proveedor externo), así que viven en su
    propio modelo 'Impresora' dentro de esta misma app. Por eso hay dos FK
    opcionales en vez de una sola: exactamente una debe estar completa,
    según 'tipo' (ver clean()).
    """

    class Tipo(models.TextChoices):
        PROYECTOR = 'PROY', 'Proyector'
        IMPRESORA = 'IMPR', 'Impresora'

    activo = models.OneToOneField(
        Activo, on_delete=models.PROTECT, null=True, blank=True,
        related_name='equipo_mantenible', verbose_name="Activo (proyectores)"
    )
    impresora = models.OneToOneField(
        Impresora, on_delete=models.PROTECT, null=True, blank=True,
        related_name='equipo_mantenible', verbose_name="Impresora"
    )
    # El tipo se guarda explícito (no se infiere del nombre de la Categoría)
    # para no depender de que alguien no cambie el texto "Proyector" en el
    # catálogo y rompa el filtrado de listas.
    tipo = models.CharField(max_length=4, choices=Tipo.choices, verbose_name="Tipo de equipo")
    activo_en_revision = models.BooleanField(
        default=True, verbose_name="Incluido en revisión mensual",
        help_text="Desmárquelo para pausar este equipo sin perder su historial. El registro nunca se elimina."
    )
    agregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Agregado por"
    )
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Equipo en Mantención"
        verbose_name_plural = "Equipos en Mantención"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(tipo='PROY', activo__isnull=False, impresora__isnull=True) |
                    models.Q(tipo='IMPR', impresora__isnull=False, activo__isnull=True)
                ),
                name='equipo_mantenible_un_solo_dueno'
            )
        ]

    def clean(self):
        super().clean()
        if self.tipo == self.Tipo.PROYECTOR and not self.activo_id:
            raise ValidationError({'activo': 'Falta seleccionar el proyector (Activo de inventario).'})
        if self.tipo == self.Tipo.IMPRESORA and not self.impresora_id:
            raise ValidationError({'impresora': 'Falta seleccionar la impresora.'})
        if self.activo_id and self.impresora_id:
            raise ValidationError('Un equipo no puede ser proyector e impresora a la vez.')

    @property
    def equipo_real(self):
        """El Activo o la Impresora real detrás de este registro, según el tipo."""
        return self.activo if self.tipo == self.Tipo.PROYECTOR else self.impresora

    @property
    def marca_modelo(self):
        if self.tipo == self.Tipo.PROYECTOR:
            return str(self.activo.catalogo) if self.activo and self.activo.catalogo else ''
        return f"{self.impresora.marca} {self.impresora.modelo}" if self.impresora else ''

    @property
    def numero_serie(self):
        equipo = self.equipo_real
        return equipo.numero_serie if equipo else ''

    @property
    def ubicacion(self):
        equipo = self.equipo_real
        return equipo.ubicacion if equipo else None

    @property
    def estado_texto(self):
        if self.tipo == self.Tipo.PROYECTOR:
            return str(self.activo.estado) if self.activo and self.activo.estado else ''
        return self.impresora.get_estado_display() if self.impresora else ''

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.equipo_real}"


class CicloRevision(models.Model):
    """
    Una ronda de revisión de UN tipo de equipo (proyector o impresora).

    No está atado a "un mes calendario": proyectores e impresoras se
    revisan con frecuencias distintas (impresoras ~2 veces por semana,
    proyectores ~1 vez al mes) y una ronda puede saltarse por falta de
    personal o tickets urgentes. Por eso el ciclo se crea explícitamente
    (botón "Nuevo ciclo/revisión" o el comando de management) con la fecha
    real en que arrancó, en vez de generarse solo el día 1 de cada mes.

    El ciclo MÁS RECIENTE de cada tipo es el único editable; los anteriores
    quedan de sólo lectura como historial (ver Revisión mensual).
    """

    tipo = models.CharField(max_length=4, choices=EquipoMantenible.Tipo.choices, verbose_name="Tipo de equipo")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_generado = models.DateTimeField(auto_now_add=True)
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Iniciado por",
        help_text="Vacío si el ciclo fue creado automáticamente por el comando programado."
    )

    class Meta:
        verbose_name = "Ciclo de Revisión"
        verbose_name_plural = "Ciclos de Revisión"
        # -id al final como desempate determinístico: MySQL guarda
        # fecha_generado con precisión de segundo, así que dos ciclos
        # creados muy seguido (mismo día, mismo segundo) necesitan otra
        # forma de saber cuál es realmente "el más reciente".
        ordering = ['-fecha_inicio', '-fecha_generado', '-id']

    def __str__(self):
        return f"Ciclo {self.fecha_inicio.strftime('%m/%Y')}, día {self.fecha_inicio.day}"


class RevisionEquipo(models.Model):
    """
    Una fila = "este equipo, en este ciclo mensual, quedó en tal estado".
    El comando mensual crea todas las filas en PENDIENTE; el practicante las
    va actualizando a OK o NOVEDAD a medida que revisa en terreno.
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'PEN', 'Pendiente'
        OK = 'OK', 'OK'
        NOVEDAD = 'NOV', 'Con Novedad'

    ciclo = models.ForeignKey(CicloRevision, on_delete=models.PROTECT, related_name='revisiones')
    equipo = models.ForeignKey(EquipoMantenible, on_delete=models.PROTECT, related_name='revisiones')
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.PENDIENTE)

    # Foto de la ubicación del equipo AL MOMENTO de generarse el ciclo: así el
    # listado "por edificio y sala" no cambia a mitad de mes si alguien
    # reubica el equipo después de generado el listado (el enroque se ve
    # reflejado recién en el ciclo siguiente).
    ubicacion_en_revision = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name='+'
    )

    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='revisiones_realizadas'
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)
    comentario = models.TextField(blank=True, verbose_name="Comentario / Novedad")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Revisión de Equipo"
        verbose_name_plural = "Revisiones de Equipos"
        constraints = [
            models.UniqueConstraint(fields=['ciclo', 'equipo'], name='unique_revision_ciclo_equipo')
        ]

    def __str__(self):
        return f"{self.equipo} - {self.ciclo} - {self.get_estado_display()}"

    def clean(self):
        super().clean()
        # Defensa adicional a la validación del formulario: una novedad sin
        # comentario deja al equipo técnico sin ninguna pista del problema.
        if self.estado == self.Estado.NOVEDAD and not self.comentario.strip():
            raise ValidationError({'comentario': 'Debes describir la novedad antes de guardarla.'})


class EvidenciaRevision(models.Model):
    """Una foto o video adjunto a una revisión con novedad (puede haber varias)."""

    class TipoArchivo(models.TextChoices):
        FOTO = 'FOTO', 'Foto'
        VIDEO = 'VIDEO', 'Video'

    revision = models.ForeignKey(RevisionEquipo, on_delete=models.PROTECT, related_name='evidencias')
    archivo = models.FileField(upload_to='mantencion/evidencias/%Y/%m/', verbose_name="Evidencia")
    tipo_archivo = models.CharField(max_length=5, choices=TipoArchivo.choices)
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evidencia de Revisión"
        verbose_name_plural = "Evidencias de Revisión"
        ordering = ['-subido_en']

    def __str__(self):
        return f"{self.get_tipo_archivo_display()} de {self.revision}"
