from django.core.management.base import BaseCommand
from openpyxl import Workbook
from adr.models import (
    MiniPC, AllInOne, SwitchDeRed, AllInOneAdmins, Notebook, 
    Proyectores, BodegaADR, Azotea, Monitor, Audio, Tablet, EquiposIsla, Televisor
)

class Command(BaseCommand):
    help = 'Exporta todos los equipos antiguos a un archivo Excel (.xlsx) para staging'

    def handle(self, *args, **options):
        self.stdout.write("Generar archivo Excel (.xlsx)...")
        
        modelos = [
            (MiniPC, 'Mini PC'), (AllInOne, 'All In One'), (SwitchDeRed, 'Switch'), 
            (AllInOneAdmins, 'AIO Admin'), (Notebook, 'Notebook'), (Proyectores, 'Proyector'),
            (BodegaADR, 'Bodega'), (Azotea, 'Azotea'), (Monitor, 'Monitor'), 
            (Audio, 'Audio'), (Tablet, 'Tablet'), (EquiposIsla, 'Isla'), (Televisor, 'TV')
        ]

        # Crear el libro y la hoja de Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Staging Activos"

        # Escribir la primera fila (Encabezados incluyendo Creado_Por)
        ws.append([
            'ID_Original', 'Tabla_Origen', 'Categoria_Base', 'Marca', 'Modelo', 
            'N_Serie', 'Etiqueta', 'BDO', 'NetBios', 'Estado', 
            'Ubicacion_Original', 'Asignado_A', 'Creado_Por', 'Fecha_Creacion'
        ])

        # Recorrer todos los modelos y extraer los datos
        for ModeloViejo, cat_default in modelos:
            for registro in ModeloViejo.objects.all():
                
                # Formatear la fecha para que Excel no tenga problemas
                fecha_str = ''
                if hasattr(registro, 'fecha_creacion') and registro.fecha_creacion:
                    fecha_str = registro.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')

                # Rescatar el nombre de usuario del creador si existe
                creado_por_str = ''
                if hasattr(registro, 'creado_por') and registro.creado_por:
                    # Asumir que el modelo de usuario tiene el campo 'username'
                    creado_por_str = registro.creado_por.username

                ws.append([
                    registro.pk,
                    ModeloViejo.__name__,
                    getattr(registro, 'activo', cat_default),
                    getattr(registro, 'marca', 'Sin Marca'),
                    getattr(registro, 'modelo', 'Genérico'),
                    getattr(registro, 'n_serie', ''),
                    getattr(registro, 'etiqueta', ''),
                    getattr(registro, 'bdo', ''),
                    getattr(registro, 'netbios', ''),
                    getattr(registro, 'estado', 'OPERATIVO'),
                    getattr(registro, 'ubicacion', ''),
                    getattr(registro, 'asignado_a', ''),
                    creado_por_str,
                    fecha_str
                ])
                
        # Guardar el archivo final
        filename = 'activos_staging.xlsx'
        wb.save(filename)
        
        self.stdout.write(self.style.SUCCESS(f"¡Exportación completada! Abre el archivo '{filename}' en tu proyecto."))