# mantencion/management/commands/generar_ciclo_salas.py
from django.core.management.base import BaseCommand
from mantencion.services import crear_ciclo_mensual_salas


class Command(BaseCommand):
    help = "Genera y abre de forma desatendida el ciclo mensual de salas de clases"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la creación incluso si ya existe un ciclo en el mes actual.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando generación automática de ciclo..."))
        
        creado, mensaje = crear_ciclo_mensual_salas(forzar=options['force'])
        
        if creado:
            self.stdout.write(self.style.SUCCESS(mensaje))
        else:
            self.stdout.write(self.style.WARNING(mensaje))