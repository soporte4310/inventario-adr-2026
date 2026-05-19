from django.db import models
from django.urls import reverse
from django.conf import settings


class Prestamo(models.Model):
    OPCIONES_ITEMS = [
        ('Mouse', 'Mouse'),
        ('Teclado', 'Teclado'),
        ('Cable HDMI', 'Cable HDMI'),
        ('Alargador', 'Alargador / Zapatilla'),
        ('Adaptador Tipo C a HDMI', 'Adaptador Tipo C a HDMI'),
        ('Adaptador VGA a HDMI', 'Adaptador VGA a HDMI'),
        ('Puntero Presentador PPT', 'Puntero / Presentador PPT'),
        ('Otro', 'Otro (Especificar en observaciones)'),
    ]
    
    OPCIONES_ESTADO = [
        ('En Préstamo', 'En Préstamo'),
        ('Devuelto', 'Devuelto'),
    ]

    docente_nombre = models.CharField(max_length=150, verbose_name='Nombre del Docente/Funcionario')
    docente_rut = models.CharField(max_length=12, verbose_name='RUT')
    sala = models.CharField(max_length=50, verbose_name='Sala / Ubicación')
    item_prestado = models.CharField(max_length=100, choices=OPCIONES_ITEMS, verbose_name='Ítem Prestado')
    
    estado = models.CharField(max_length=50, choices=OPCIONES_ESTADO, default='En Préstamo', verbose_name='Estado')
    
    fecha_prestamo = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Préstamo')
    fecha_devolucion = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Devolución')
    observaciones = models.TextField(null=True, blank=True, verbose_name='Observaciones')
    
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='Registrado por'
    )

    class Meta:
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'
        ordering = ['-fecha_prestamo'] # Los más recientes primero

    def __str__(self):
        return f"{self.item_prestado} a {self.docente_nombre} ({self.sala})"