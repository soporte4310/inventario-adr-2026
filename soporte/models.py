from django.db import models
from django.utils import timezone
from inventario.models import Funcionario


class RegistroListaNegra(models.Model):
    """
    Expediente que asocia a un funcionario a la lista negra oficial de ADR.
    """
    class NivelAlerta(models.TextChoices):
        OBSERVACION = 'OBSERVACION', 'En Observación'
        RESTRINGIDO = 'RESTRINGIDO', 'Acceso Restringido'
        PELIGRO_PUBLICO = 'PELIGRO_PUBLICO', 'Peligro extremo'

    funcionario = models.OneToOneField(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='lista_negra',
        verbose_name="Funcionario"
    )
    fecha_ingreso = models.DateField(
        verbose_name="Fecha de ingreso a la lista",
        default=timezone.now
    )
    nivel_alerta = models.CharField(
        verbose_name="Nivel de alerta",
        max_length=20,
        choices=NivelAlerta.choices,
        default=NivelAlerta.OBSERVACION
    )
    alias_o_apodo = models.CharField(
        verbose_name="Alias / Apodo técnico",
        max_length=100,
        blank=True,
        null=True,
        help_text="Ej: 'El terror de las bandejas', 'Destructora de tóners'."
    )
    activo = models.BooleanField(
        verbose_name="Activo en lista negra",
        default=True,
        help_text="Desmarcar si la persona ya fue indultada por Soporte."
    )
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Expediente Lista Negra"
        verbose_name_plural = "Expedientes Lista Negra"
        ordering = ['-fecha_ingreso']

    def __str__(self):
        return f"{self.funcionario.nombre} ({self.get_nivel_alerta_display()})"


class FaltaListaNegra(models.Model):
    """
    Detalle individual de cada incidente cometido por el funcionario fichado.
    """
    class Gravedad(models.TextChoices):
        LEVE = 'LEVE', 'Leve (Reinicio solucionaba el problema)'
        MODERADA = 'MODERADA', 'Moderada (Riesgo para insumos/hardware)'
        GRAVE = 'GRAVE', 'Grave (Destrucción de insumos / Fuerza bruta)'

    registro = models.ForeignKey(
        RegistroListaNegra,
        on_delete=models.CASCADE,
        related_name='faltas',
        verbose_name="Expediente"
    )
    descripcion = models.TextField(
        verbose_name="Descripción de la falta",
        help_text="Ej: 'Forzó la bandeja 1 con 80 hojas y apagó la zapatilla con el pie'."
    )
    fecha_suceso = models.DateField(
        verbose_name="Fecha del suceso",
        default=timezone.now
    )
    gravedad = models.CharField(
        verbose_name="Gravedad de la falta",
        max_length=15,
        choices=Gravedad.choices,
        default=Gravedad.LEVE
    )
    compensacion = models.CharField(
        null=True,
        blank=True,
        verbose_name="Tributo exigido",
        max_length=150,
        help_text="Lo necesario para desestimar este cargo."
    )
    resuelta = models.BooleanField(
        verbose_name="¿Falta saldada?",
        default=False
    )
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Falta registrada"
        verbose_name_plural = "Faltas registradas"
        ordering = ['-fecha_suceso']

    def __str__(self):
        return f"[{self.fecha_suceso}] {self.get_gravedad_display()} - {self.descripcion[:40]}"