from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

from common.validators import (
    validador_alfanumerico_nombres, validador_codigo_estricto, validador_mac,
    validador_nombre_red, validador_solo_numeros, validador_texto_seguro,
)
from inventario.models import Activo, Ubicacion

User = get_user_model()


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

    # El valor guardado es igual a la etiqueta (en vez de un código corto)
    # porque los datos reales ya existentes usan ese mismo texto exacto
    # ('Blanco y Negro' / 'Color'), así que no requiere migrar datos.
    class TipoImpresion(models.TextChoices):
        BLANCO_Y_NEGRO = 'Blanco y Negro', 'Blanco y Negro'
        COLOR = 'Color', 'Color'

    marca = models.CharField(
        max_length=50, default='HP', verbose_name="Marca",
        validators=[validador_alfanumerico_nombres]
    )
    modelo = models.CharField(
        max_length=50, verbose_name="Modelo",
        validators=[validador_codigo_estricto]
    )
    tipo_impresion = models.CharField(
        max_length=30, blank=True, choices=TipoImpresion.choices, verbose_name="Tipo de impresión",
    )
    rango_impresiones = models.CharField(
        max_length=30, blank=True, verbose_name="Rango de impresiones contratado",
        validators=[validador_alfanumerico_nombres]
    )
    nombre_equipo = models.CharField(
        max_length=100, blank=True, verbose_name="Nombre de red",
        help_text="Hostname asignado por el proveedor, ej: IQQ_E540_BODEGA",
        validators=[validador_nombre_red]
    )
    numero_serie = models.CharField(
        max_length=50, unique=True, verbose_name="N° de Serie",
        validators=[validador_codigo_estricto]
    )
    # Antes era GenericIPAddressField, pero eso exige una IPv4 completa y
    # válida siempre. En la práctica bastantes impresoras no tienen una IP
    # fija (la asigna el router por DHCP), así que se relajó a texto libre
    # (ip_automatica cubre ese caso explícitamente) en vez de forzar un
    # formato que no siempre corresponde.
    ip = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="IP",
        validators=[validador_texto_seguro]
    )
    ip_automatica = models.BooleanField(
        default=False, verbose_name="Automático (DHCP)",
        help_text="Márquelo si la IP la asigna el router automáticamente (no tiene IP fija)."
    )
    mac = models.CharField(max_length=17, blank=True, verbose_name="MAC", validators=[validador_mac])
    codigo_proveedor = models.CharField(
        # No es unique: en la práctica el proveedor a veces repite este
        # código entre equipos distintos (ej: por contrato/lote). El N° de
        # Serie es el identificador confiable, ese sí es único.
        max_length=30, blank=True, null=True, verbose_name="Código del proveedor",
        validators=[validador_solo_numeros]
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

    def save(self, *args, **kwargs):
        # Si es DHCP, la IP fija queda obsoleta/contradictoria: se limpia acá
        # para que no quede dato manual desactualizado junto a la marca.
        if self.ip_automatica:
            self.ip = ''
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.numero_serie}"










class CicloRevision(models.Model):
    """
    Representa el período mensual de inspección preventiva.
    Controla el ciclo de vida (apertura, avance y cierre auditado)
    para un tipo de revisión específico (Salas, Impresoras, etc.).
    """

    class TipoCiclo(models.TextChoices):
        SALAS = "SALAS", "Revisión de Salas (Audiovisual y Red)"
        IMPRESORAS = "IMPRESORAS", "Revisión de Impresoras (Flota y Contadores)"

    class EstadoCiclo(models.TextChoices):
        EN_CURSO = "EN_CURSO", "En Curso"
        FINALIZADO = "FINALIZADO", "Finalizado / Cerrado"

    nombre = models.CharField(
        max_length=120,
        help_text="Ej: 'Revisión Preventiva Salas - Noviembre 2026'",
    )
    tipo = models.CharField(
        max_length=20, choices=TipoCiclo.choices, default=TipoCiclo.SALAS
    )
    estado = models.CharField(
        max_length=20, choices=EstadoCiclo.choices, default=EstadoCiclo.EN_CURSO
    )

    # Fechas operativas
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_limite = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha estimada para completar el ciclo (ej: fin de mes)",
    )
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Marca de tiempo exacta en que se cerró el ciclo formalmente",
    )

    # Auditoría de usuarios
    creado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="ciclos_creados",
        null=True,
        blank=True,
    )
    cerrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="ciclos_cerrados",
        null=True,
        blank=True,
    )

    observaciones_cierre = models.TextField(
        blank=True,
        help_text="Resumen o justificación al cerrar (ej: 'Quedaron 2 salas pendientes por remodelación')",
    )

    class Meta:
        verbose_name = "Ciclo de Mantenimiento"
        verbose_name_plural = "Ciclos de Mantenimiento"
        ordering = ["-fecha_inicio", "-id"]

    def __str__(self):
        return f"{self.nombre} [{self.get_estado_display()}]"

    # ----------------------------------------------------
    # PROPIEDADES DE MÉTRICAS Y AVANCE (Para el Dashboard y Listados)
    # ----------------------------------------------------

    @property
    def total_salas(self):
        return self.revisiones_salas.count()

    @property
    def total_revisadas(self):
        return self.revisiones_salas.exclude(
            estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE
        ).count()

    @property
    def total_pendientes(self):
        return self.revisiones_salas.filter(
            estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE
        ).count()

    @property
    def porcentaje_avance(self):
        total = self.total_salas
        if total == 0:
            return 0
        return round((self.total_revisadas / total) * 100)

    @property
    def total_operativas(self):
        return self.revisiones_salas.filter(
            estado_general=RevisionSala.EstadoGeneralSala.OPERATIVA
        ).count()

    @property
    def total_con_observaciones(self):
        return self.revisiones_salas.filter(
            estado_general=RevisionSala.EstadoGeneralSala.CON_OBSERVACIONES
        ).count()

    @property
    def total_criticas(self):
        return self.revisiones_salas.filter(
            estado_general=RevisionSala.EstadoGeneralSala.CRITICA
        ).count()

    # ----------------------------------------------------
    # MÉTODOS DE NEGOCIO
    # ----------------------------------------------------

    def poblar_salas_automaticamente(self):
        """
        Crea los registros de RevisionSala para todas las ubicaciones
        marcadas con aplica_mantenimiento=True. Vincula automáticamente
        el proyector que esté asignado actualmente a cada sala en inventario.
        """
        if self.tipo != self.TipoCiclo.SALAS:
            return

        ubicaciones = Ubicacion.objects.filter(aplica_mantenimiento=True)

        nuevas_revisiones = []
        for ubicacion in ubicaciones:
            # Detectar si la sala tiene proyector registrado hoy
            proyector_asignado = Activo.objects.filter(
                ubicacion=ubicacion,
                categoria__nombre__iexact="PROYECTOR",
                is_deleted=False,
            ).first()

            nuevas_revisiones.append(
                RevisionSala(
                    ciclo=self,
                    ubicacion=ubicacion,
                    proyector=proyector_asignado,
                    estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE,
                )
            )

        # Inserción masiva eficiente en una sola transacción SQL
        RevisionSala.objects.bulk_create(nuevas_revisiones, ignore_conflicts=True)

    def cerrar_ciclo(self, usuario, observaciones=""):
        """Finaliza el ciclo preventivo y congela la fecha de auditoría."""
        self.estado = self.EstadoCiclo.FINALIZADO
        self.cerrado_por = usuario
        self.fecha_cierre = timezone.now()
        self.observaciones_cierre = observaciones
        self.save()




class RevisionSala(models.Model):
    """Contiene la auditoría técnica y audiovisual de un recinto en un ciclo mensual."""
    class NivelEstado(models.TextChoices):
        BUENO = 'BUENO', 'Bueno (OK)'
        REGULAR = 'REGULAR', 'Regular (Con Observaciones / Falso contacto)'
        MALO = 'MALO', 'Malo (Inoperativo)'

    class EstadoGeneralSala(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Revisión'
        OPERATIVA = 'OPERATIVA', 'Operativa'
        CON_OBSERVACIONES = 'OBSERVACION', 'Operativa con Observaciones'
        CRITICA = 'CRITICA', 'Fuera de Servicio'

    ciclo = models.ForeignKey(CicloRevision, on_delete=models.CASCADE, related_name='revisiones_salas')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='revisiones_mantenimiento')
    operador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Estado global de la sala calculado
    estado_general = models.CharField(
        max_length=20, 
        choices=EstadoGeneralSala.choices, 
        default=EstadoGeneralSala.OPERATIVA
    )

    # ----------------------------------------------------
    # PROYECTOR
    # ----------------------------------------------------
    proyector = models.ForeignKey(Activo, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Encendido general
    proyector_encendido = models.CharField(
        max_length=10, 
        choices=NivelEstado.choices, 
        default=NivelEstado.BUENO,
        help_text="Bueno: OK | Regular: Demora, imagen opaca o advertencia de lámpara | Malo: No prende/quemado",
    )

    horas_lampara = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="(Opcional) Horas registradas en menú OSD si se revisan"
    )

    # Red y conectividad del proyector
    red_proyector_conectada = models.CharField(
        max_length=10, 
        choices=NivelEstado.choices, 
        default=NivelEstado.BUENO,
        help_text="¿Cable conectado y con link de red?"
    )
    proyeccion_inalambrica = models.CharField(
        max_length=10, 
        choices=NivelEstado.choices, 
        default=NivelEstado.BUENO,
        help_text="Disponibilidad de casting / red inalámbrica"
    )
    candado_proyector = models.CharField(
            max_length=10, 
            choices=NivelEstado.choices, 
            default=NivelEstado.BUENO,
            help_text="¿La jaula del proyector está con candado?"
        )

    # ----------------------------------------------------
    # INFRAESTRUCTURA DE LA SALA (Mesa docente / Muros)
    # ----------------------------------------------------
    copla_hdmi = models.CharField(
        max_length=10, 
        choices=NivelEstado.choices, 
        default=NivelEstado.BUENO,
        help_text="Bueno: firme y con señal | Regular: suelta/parpadea si se mueve | Malo: quebrada/sin video"
    )
    
    panel_control = models.CharField(
        max_length=10, 
        choices=NivelEstado.choices, 
        default=NivelEstado.BUENO,
        help_text="Bueno: todo ok | Regular: enciende pero fallan otros botones | Malo: no responde"
    )
    
    puerto_red_pared = models.CharField(
        max_length=10, 
        choices=NivelEstado.choices, 
        default=NivelEstado.BUENO,
        help_text="Punto de red en pared para el computador docente"
    )
    
    audio_sala = models.CharField(
        max_length=10, 
        choices=NivelEstado.choices, 
        default=NivelEstado.BUENO,
        help_text="Bueno: audio limpio | Regular: chicharreo / un parlante mudo | Malo: sin audio"
    )

    # ----------------------------------------------------
    # EVIDENCIA Y REGISTRO
    # ----------------------------------------------------
    # Almacena la URL devuelta por Cloudinary
    video_evidencia_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="Video de evidencia (Audio/Video)",
        help_text="URL del video corto de prueba almacenado en Cloudinary"
    )
    # Trazabilidad
    fecha_revision = models.DateTimeField(null=True, blank=True)
    # Notas para justificar cualquier elemento en Amarillo o Rojo
    observaciones = models.TextField(
        blank=True, 
        help_text="Ej: Copla HDMI suelta; Foco con advertencia de 3500 hrs"
    )

    class Meta:
        verbose_name = "Revisión de Sala"
        verbose_name_plural = "Revisiones de Salas"
        unique_together = ('ciclo', 'ubicacion')
        ordering = ['ubicacion__nombre']

    def save(self, *args, **kwargs):
        """Calcula el estado general de la sala una vez inspeccionada."""
        # Si ya fue revisada (hay fecha o video de evidencia cargado)
        if self.fecha_revision or self.video_evidencia_url:
            if not self.fecha_revision:
                self.fecha_revision = timezone.now()

            estados = [
                self.proyector_encendido,
                self.estado_lampara,
                self.red_proyector_conectada,
                self.proyeccion_inalambrica,
                self.candado_proyector,
                self.copla_hdmi,
                self.panel_control,
                self.puerto_red_pared,
                self.audio_sala,
            ]

            # Si falla algo indispensable para dictar clase
            if (
                self.proyector_encendido == self.NivelEstado.MALO
                or self.copla_hdmi == self.NivelEstado.MALO
                or self.estado_lampara == self.NivelEstado.MALO
            ):
                self.estado_general = self.EstadoGeneralSala.CRITICA
            elif self.NivelEstado.MALO in estados or self.NivelEstado.REGULAR in estados:
                self.estado_general = self.EstadoGeneralSala.CON_OBSERVACIONES
            else:
                self.estado_general = self.EstadoGeneralSala.OPERATIVA
        else:
            # Si nadie ha enviado la revisión formal aún
            self.estado_general = self.EstadoGeneralSala.PENDIENTE

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ubicacion.nombre} - {self.ciclo.nombre} [{self.get_estado_general_display()}]"