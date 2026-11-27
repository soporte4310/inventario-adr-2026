from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

from common.validators import (
    validador_alfanumerico_nombres, validador_codigo_estricto, validador_mac,
    validador_nombre_red, validador_solo_numeros, validador_texto_seguro,
)
from inventario.models import Activo, ActivoImpresora, Ubicacion

User = get_user_model()




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

    @property
    def esta_cerrado(self):
        return self.estado == self.EstadoCiclo.FINALIZADO

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



    @property
    def total_impresoras(self):
        return self.revisiones_impresoras.count()

    @property
    def total_impresoras_revisadas(self):
        return self.revisiones_impresoras.exclude(
            estado_general=RevisionImpresora.EstadoGeneral.PENDIENTE
        ).count()

    @property
    def total_impresoras_pendientes(self):
        return self.revisiones_impresoras.filter(
            estado_general=RevisionImpresora.EstadoGeneral.PENDIENTE
        ).count()

    @property
    def total_impresoras_operativas(self):
        return self.revisiones_impresoras.filter(
            estado_general=RevisionImpresora.EstadoGeneral.OPERATIVA
        ).count()

    @property
    def total_impresoras_no_operativas(self):
        return self.revisiones_impresoras.filter(
            estado_general=RevisionImpresora.EstadoGeneral.NO_OPERATIVA
        ).count()

    @property
    def porcentaje_avance_impresoras(self):
        total = self.total_impresoras
        if total == 0:
            return 0
        return round((self.total_impresoras_revisadas / total) * 100)

    def poblar_impresoras_automaticamente(self):
        """
        Crea los registros de RevisionImpresora para todas las impresoras
        activas en el sistema que no hayan sido dadas de baja en inventario.
        """
        if self.tipo != self.TipoCiclo.IMPRESORAS:
            return

        # Selecciona las impresoras vigentes (excluye eliminadas lógicamente y de baja)
        impresoras_activas = ActivoImpresora.objects.filter(
            activo__is_deleted=False
        ).exclude(
            activo__estado__nombre__icontains='BAJA'
        ).select_related('activo')

        nuevas_revisiones = [
            RevisionImpresora(
                ciclo=self,
                impresora=impresora,
                estado_general=RevisionImpresora.EstadoGeneral.PENDIENTE
            )
            for impresora in impresoras_activas
        ]

        RevisionImpresora.objects.bulk_create(nuevas_revisiones, ignore_conflicts=True)




class RevisionSala(models.Model):
    """Contiene la auditoría técnica y audiovisual de una ubicación en un ciclo de revisión mensual."""
    class NivelEstado(models.TextChoices):
        BUENO = 'BUENO', 'Bueno (OK)'
        REGULAR = 'REGULAR', 'Regular (Con Observaciones / Falso contacto)'
        MALO = 'MALO', 'Malo (Inoperativo)'
        NO_APLICA = 'NA', 'No Aplica'

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
        default=EstadoGeneralSala.PENDIENTE
    )

    # ----------------------------------------------------
    # PROYECTOR
    # ----------------------------------------------------
    proyector = models.ForeignKey(Activo, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Encendido general
    proyector_encendido = models.CharField(
        max_length=10,
        null=True,
        blank=True, 
        choices=NivelEstado.choices, 
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
        null=True,
        blank=True,
        choices=NivelEstado.choices, 
        help_text="¿Cable conectado y con link de red?"
    )
    proyeccion_inalambrica = models.CharField(
        max_length=10, 
        null=True,
        blank=True,
        choices=NivelEstado.choices, 
        help_text="Disponibilidad de casting / red inalámbrica"
    )
    candado_proyector = models.CharField(
        max_length=10, 
        null=True,
        blank=True,
        choices=NivelEstado.choices, 
        help_text="¿La jaula del proyector está con candado?"
    )

    # ----------------------------------------------------
    # INFRAESTRUCTURA DE LA SALA (Mesa docente / Muros)
    # ----------------------------------------------------
    copla_hdmi = models.CharField(
        max_length=10, 
        null=True,
        blank=True,
        choices=NivelEstado.choices, 
        help_text="Bueno: firme y con señal | Regular: suelta/parpadea si se mueve | Malo: quebrada/sin video"
    )
    
    panel_control = models.CharField(
        max_length=10, 
        null=True,
        blank=True,
        choices=NivelEstado.choices, 
        help_text="Bueno: todo ok | Regular: enciende pero fallan otros botones | Malo: no responde"
    )
    
    puerto_red_pared = models.CharField(
        max_length=10,
        null=True,
        blank=True, 
        choices=NivelEstado.choices, 
        help_text="Punto de red en pared para el computador docente"
    )
    
    audio_sala = models.CharField(
        max_length=10, 
        null=True,
        blank=True,
        choices=NivelEstado.choices, 
        help_text="Bueno: audio limpio | Regular: chicharreo / un parlante mudo | Malo: sin audio"
    )

    # ----------------------------------------------------
    # EVIDENCIA Y REGISTRO
    # ----------------------------------------------------
    # Almacena la URL devuelta por Cloudinary
    video_evidencia_url = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="Video de evidencia",
        help_text="Ruta local o URL remota de Cloudinary"
    )
    # Se guarda una captura del primer frame del video subido
    imagen_evidencia = models.ImageField(
        verbose_name="Miniatura de Evidencia",
        upload_to="evidencias_salas/thumbnails/main/",
        max_length=255,
        blank=True,
        null=True
    )
    imagen_thumb_medium = models.ImageField(
        verbose_name="Thumbnail (600x600)",
        upload_to="evidencias_salas/thumbnails/medium/",
        max_length=255,
        blank=True,
        null=True,
        editable=False
    )
    imagen_thumb_small = models.ImageField(
        verbose_name="Thumbnail (50x50)",
        upload_to="evidencias_salas/thumbnails/small/",
        max_length=255,
        blank=True,
        null=True,
        editable=False
    )

    # Trazabilidad
    fecha_revision = models.DateTimeField(null=True, blank=True)
    # Notas para justificar cualquier elemento en Amarillo o Rojo
    observaciones = models.TextField(
        blank=True, 
        help_text="Ej: Copla HDMI suelta; Foco con advertencia de 3500 hrs"
    )

    @property
    def tiene_video(self):
        """Indica si la sala cuenta con un video de evidencia cargado."""
        return bool(self.video_evidencia_url and self.video_evidencia_url.strip())

    @property
    def checklist_completado(self):
        """Indica si todos los campos obligatorios del formulario fueron respondidos."""
        campos_obligatorios = [
            self.copla_hdmi,
            self.panel_control,
            self.puerto_red_pared,
            self.audio_sala,
        ]
        if self.proyector_id:
            campos_obligatorios.extend([
                self.proyector_encendido,
                self.red_proyector_conectada,
                self.proyeccion_inalambrica,
                self.candado_proyector,
            ])
        return not any(v in (None, '') for v in campos_obligatorios)

    class Meta:
        verbose_name = "Revisión de Sala"
        verbose_name_plural = "Revisiones de Salas"
        unique_together = ('ciclo', 'ubicacion')
        ordering = ['ubicacion__nombre']

    def save(self, *args, **kwargs):
        """
        Calcula el estado general de forma automatizada solo cuando
        el checklist está respondido Y el video de evidencia fue subido.
        """
        # Si ya existe en la BD (edición) y su ciclo está FINALIZADO, prohibir cualquier cambio.
        if self.pk and self.ciclo.estado == CicloRevision.EstadoCiclo.FINALIZADO:
            raise ValidationError("No se puede modificar una revisión que pertenece a un ciclo cerrado.")
        
        # Si se llamó save(update_fields=[...]), garantizamos que estado_general se actualice en BD
        if kwargs.get('update_fields') is not None:
            fields = set(kwargs['update_fields'])
            fields.update({'estado_general', 'fecha_revision'})
            kwargs['update_fields'] = list(fields)

        # Regla 1: Si falta el checklist O falta el video, la revisión sigue PENDIENTE
        if not self.checklist_completado or not self.tiene_video:
            self.estado_general = self.EstadoGeneralSala.PENDIENTE
            super().save(*args, **kwargs)
            return

        # Si llegamos aquí, están completos TANTO el checklist COMO el video
        if not self.fecha_revision:
            self.fecha_revision = timezone.now()

        # Regla 2: Sala requiere proyección por catálogo y carece de proyector -> CRITICA
        if self.ubicacion.requiere_proyeccion and not self.proyector:
            self.estado_general = self.EstadoGeneralSala.CRITICA
            super().save(*args, **kwargs)
            return

        # Lista completa de campos evaluados
        todos_los_campos = [
            self.copla_hdmi,
            self.panel_control,
            self.puerto_red_pared,
            self.audio_sala,
        ]
        if self.proyector:
            todos_los_campos.extend([
                self.proyector_encendido,
                self.red_proyector_conectada,
                self.proyeccion_inalambrica,
                self.candado_proyector,
            ])

        # Filtrar únicamente los ítems evaluables (ignoramos los 'NA')
        evaluables = [v for v in todos_los_campos if v != self.NivelEstado.NO_APLICA]

        # Regla 3: Clasificación semafórica
        es_falla_critica = (
            (self.proyector and self.proyector_encendido == self.NivelEstado.MALO) or
            (self.copla_hdmi == self.NivelEstado.MALO)
        )

        if es_falla_critica:
            self.estado_general = self.EstadoGeneralSala.CRITICA
        elif self.NivelEstado.MALO in evaluables or self.NivelEstado.REGULAR in evaluables:
            self.estado_general = self.EstadoGeneralSala.CON_OBSERVACIONES
        else:
            self.estado_general = self.EstadoGeneralSala.OPERATIVA

        super().save(*args, **kwargs)




class RevisionImpresora(models.Model):
    """
    Registra la inspección técnica preventiva mensual de una impresora o multifuncional.
    Permite validar de forma rápida su operatividad técnica y registrar incidencias u observaciones.
    """

    class EstadoGeneral(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Revisión'
        OPERATIVA = 'OPERATIVA', 'Operativa'
        NO_OPERATIVA = 'NO_OPERATIVA', 'No Operativa / Con Falla'

    ciclo = models.ForeignKey(
        CicloRevision,
        on_delete=models.CASCADE,
        related_name='revisiones_impresoras',
        verbose_name="Ciclo de Mantenimiento"
    )
    impresora = models.ForeignKey(
        ActivoImpresora,
        on_delete=models.PROTECT,
        related_name='revisiones_mantenimiento',
        verbose_name="Impresora"
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Técnico / Operador"
    )

    # Evaluación técnica
    esta_operativa = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="¿Está operativa?",
        help_text="Indica si la impresora enciende, conecta a la red e imprime correctamente."
    )
    estado_general = models.CharField(
        max_length=20,
        choices=EstadoGeneral.choices,
        default=EstadoGeneral.PENDIENTE,
        verbose_name="Estado de la Revisión"
    )

    # Trazabilidad y detalle
    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Revisión"
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones / Incidencias",
        help_text="Detalle atascos recurrentes, mensaje de error en pantalla, falta de tóner o solicitud de insumos a SONDA."
    )

    class Meta:
        verbose_name = "Revisión de Impresora"
        verbose_name_plural = "Revisiones de Impresoras"
        unique_together = ('ciclo', 'impresora')
        ordering = ['impresora__activo__ubicacion__nombre', 'impresora__activo__catalogo__modelo']

    def __str__(self):
        return f"{self.impresora} - {self.get_estado_general_display()} ({self.ciclo.nombre})"

    def clean(self):
        super().clean()
        # Impedir modificaciones si el ciclo mensual ya fue cerrado formalmente
        if self.pk and self.ciclo.estado == CicloRevision.EstadoCiclo.FINALIZADO:
            raise ValidationError("No se puede modificar una revisión que pertenece a un ciclo cerrado.")

    def save(self, *args, **kwargs):
        # Asegurar consistencia de campos al actualizar solo columnas específicas
        if kwargs.get('update_fields') is not None:
            fields = set(kwargs['update_fields'])
            fields.update({'estado_general', 'fecha_revision'})
            kwargs['update_fields'] = list(fields)

        # Regla de cálculo automático del estado
        if self.esta_operativa is None:
            self.estado_general = self.EstadoGeneral.PENDIENTE
        elif self.esta_operativa is True:
            self.estado_general = self.EstadoGeneral.OPERATIVA
            if not self.fecha_revision:
                self.fecha_revision = timezone.now()
        else:
            self.estado_general = self.EstadoGeneral.NO_OPERATIVA
            if not self.fecha_revision:
                self.fecha_revision = timezone.now()

        super().save(*args, **kwargs)