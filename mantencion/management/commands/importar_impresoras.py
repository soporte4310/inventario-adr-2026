import unicodedata

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from inventario.models import Ubicacion
from mantencion.models import EquipoMantenible, Impresora

User = get_user_model()


def _normalizar(texto):
    """Minúsculas, sin tildes y sin espacios, para comparar nombres de ubicación con tolerancia."""
    sin_tildes = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
    return ''.join(sin_tildes.lower().split())


class Command(BaseCommand):
    """
    Importa el listado oficial de impresoras de un proveedor externo (hoy
    Sonda) desde un Excel, creando una Impresora + su EquipoMantenible por
    cada fila. Es idempotente por N° de Serie: correrlo de nuevo con el
    mismo archivo no duplica nada, sólo agrega las filas nuevas que
    encuentre.

    El Excel esperado tiene, a partir de la fila 2, las columnas (con
    celdas combinadas para MODELO/TIPO IMPRESIÓN/RANGO IMPRESIONES, que
    este comando "rellena hacia abajo"):
    N° MODELOS | IMAGEN REFERENCIAL | MODELO | TIPO IMPRESIÓN |
    RANGO IMPRESIONES | NOMBRE | IP | SERIE | MAC | UBICACIÓN |
    CODIGO SONDA | TOTALES

    La UBICACIÓN viene como texto libre del proveedor (ej: "Oficina DAE /
    ED-A / P1"): se intenta calzar la primera parte contra una Ubicacion
    real de 'inventario' por nombre (ignorando tildes/mayúsculas). Si no
    hay un calce único, la impresora queda SIN ubicación asignada (nunca
    se crea ni se modifica una Ubicacion automáticamente, para no tocar
    la estructura de inventario sin que alguien lo revise a mano).
    """
    help = 'Importa impresoras desde el Excel oficial del proveedor (una Impresora + EquipoMantenible por fila).'

    def add_arguments(self, parser):
        parser.add_argument('ruta_excel', help='Ruta al archivo .xlsx con el listado de impresoras.')
        parser.add_argument('--hoja', default=0, help='Nombre o índice de la hoja (por defecto, la primera).')
        parser.add_argument('--usuario', default=None, help='username a registrar como "agregado_por" (opcional).')

    def handle(self, *args, **options):
        ruta = options['ruta_excel']
        try:
            df = pd.read_excel(ruta, sheet_name=options['hoja'], header=1)
        except FileNotFoundError:
            raise CommandError(f"No se encontró el archivo: {ruta}")

        columnas_merge = ['N° MODELOS', 'MODELO', 'TIPO IMPRESIÓN', 'RANGO IMPRESIONES']
        columnas_presentes = [c for c in columnas_merge if c in df.columns]
        df[columnas_presentes] = df[columnas_presentes].ffill()

        # La fila de "TOTALES" al final no tiene N° de Serie: la descartamos.
        df = df[df['SERIE'].notna()]

        usuario = None
        if options['usuario']:
            try:
                usuario = User.objects.get(username=options['usuario'])
            except User.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"Usuario '{options['usuario']}' no existe; se deja 'agregado_por' vacío."))

        ubicaciones_por_nombre = {}
        for ubicacion in Ubicacion.objects.select_related('piso__edificio').all():
            ubicaciones_por_nombre.setdefault(_normalizar(ubicacion.nombre), []).append(ubicacion)

        creadas, existentes, sin_ubicacion = [], [], []

        for _, fila in df.iterrows():
            serie = str(fila['SERIE']).strip()
            if Impresora.objects.filter(numero_serie=serie).exists():
                existentes.append(serie)
                continue

            texto_ubicacion = str(fila.get('UBICACIÓN', '') or '')
            nombre_sala = texto_ubicacion.split('/')[0].strip()
            clave = _normalizar(nombre_sala)

            candidatos = ubicaciones_por_nombre.get(clave, [])
            if not candidatos:
                # Sin calce exacto: probamos coincidencia parcial en
                # cualquier dirección (ej: Sonda dice "CreaEmpresas", el
                # inventario tiene "Crea Empresa"). Sólo la usamos si hay
                # UN único nombre de inventario que matchea, para no
                # adivinar mal entre varios parecidos.
                nombres_parciales = [
                    clave_inv for clave_inv, u in ubicaciones_por_nombre.items()
                    if len(u) == 1 and (clave in clave_inv or clave_inv in clave)
                ]
                if len(nombres_parciales) == 1:
                    candidatos = ubicaciones_por_nombre[nombres_parciales[0]]
            ubicacion = candidatos[0] if len(candidatos) == 1 else None

            modelo_completo = str(fila.get('MODELO', '') or '').strip()
            marca, _, modelo = modelo_completo.partition(' ')
            marca = marca or 'HP'
            modelo = modelo or modelo_completo

            codigo = fila.get('CODIGO SONDA')
            codigo_texto = str(int(codigo)) if pd.notna(codigo) else ''

            impresora = Impresora.objects.create(
                marca=marca,
                modelo=modelo,
                tipo_impresion=str(fila.get('TIPO IMPRESIÓN', '') or '').strip(),
                rango_impresiones=str(fila.get('RANGO IMPRESIONES', '') or '').strip(),
                nombre_equipo=str(fila.get('NOMBRE', '') or '').strip(),
                numero_serie=serie,
                ip=str(fila.get('IP', '') or '').strip() or None,
                mac=str(fila.get('MAC', '') or '').strip(),
                codigo_proveedor=codigo_texto or None,
                ubicacion=ubicacion,
                creado_por=usuario,
            )
            EquipoMantenible.objects.create(
                tipo=EquipoMantenible.Tipo.IMPRESORA, impresora=impresora, agregado_por=usuario
            )

            if ubicacion:
                creadas.append((impresora, ubicacion))
            else:
                sin_ubicacion.append((impresora, texto_ubicacion))

        self.stdout.write(self.style.SUCCESS(f"Impresoras creadas: {len(creadas)}"))
        for impresora, ubicacion in creadas:
            self.stdout.write(f"   OK  {impresora}  ->  {ubicacion}")

        if existentes:
            self.stdout.write(self.style.WARNING(f"Ya existían (se omitieron): {len(existentes)}"))
            for serie in existentes:
                self.stdout.write(f"   -- {serie}")

        if sin_ubicacion:
            self.stdout.write(self.style.WARNING(f"Creadas SIN ubicación asignada (revisar a mano): {len(sin_ubicacion)}"))
            for impresora, texto_original in sin_ubicacion:
                self.stdout.write(f"   ?? {impresora}  (Sonda dice: \"{texto_original}\")")
