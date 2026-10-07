from django.core.management.base import BaseCommand

from mantencion.models import EquipoMantenible
from mantencion.utils import crear_nuevo_ciclo


class Command(BaseCommand):
    """
    Crea explícitamente un nuevo ciclo de revisión para UN tipo de equipo
    (proyector o impresora) con la fecha de hoy, y una fila 'Pendiente' por
    cada equipo activo de ese tipo en el roster de mantención.

    Proyectores e impresoras se revisan con frecuencias distintas, así que
    cada tipo se agenda por separado (llamar el comando una vez por tipo,
    con la periodicidad que corresponda a cada uno). A diferencia de la
    versión anterior, NO es idempotente por mes: cada ejecución abre un
    ciclo nuevo, igual que el botón "Nuevo ciclo/revisión" del sitio.
    """
    help = 'Crea un nuevo ciclo de revisión para el tipo de equipo indicado.'

    def add_arguments(self, parser):
        parser.add_argument(
            'tipo',
            choices=list(EquipoMantenible.Tipo.values),
            help="Tipo de equipo del ciclo: PROY (proyectores) o IMPR (impresoras)."
        )

    def handle(self, *args, **options):
        ciclo, cantidad = crear_nuevo_ciclo(options['tipo'])
        self.stdout.write(self.style.SUCCESS(
            f"{ciclo} ({ciclo.get_tipo_display()}): {cantidad} equipos agregados a la revisión."
        ))
