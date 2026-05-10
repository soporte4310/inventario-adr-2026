import pandas as pd
import re
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model # Para poder buscar al usuario que creó el registro
from django.utils.timezone import make_aware, is_naive
from inventario.models import (
    Activo, Catalogo, Categoria, Marca, Estado, Funcionario, Ubicacion, MapeoUbicacion
)

class Command(BaseCommand):
    help = 'Lee el archivo Excel limpio y carga los registros definitivos al modelo Activo'

    def limpiar_dato(self, valor, solo_numeros=False):
        """Limpiar la basura de Pandas y extraer la información real"""
        if pd.isnull(valor): 
            return None
        
        s = str(valor).strip()
        if s.endswith('.0'): 
            s = s[:-2]
            
        if s.upper() in ['NAN', 'NONE', '', 'N/A', '0', '-']: 
            return None
            
        if solo_numeros:
            s = re.sub(r'\D', '', s)
            if not s:
                return None
                
        return s

    def handle(self, *args, **options):
        archivo_excel = 'activos_staging_limpio.xlsx'
        self.stdout.write(self.style.WARNING(f"Leer archivo {archivo_excel}..."))

        try:
            df = pd.read_excel(archivo_excel)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"No se encontró el archivo {archivo_excel} en la raíz."))
            return

        User = get_user_model() # Obtener el modelo de usuarios activo en Django
        migrados_exito = 0
        errores = 0

        self.stdout.write("Iniciar volcado a la base de datos...")

        for index, row in df.iterrows():
            id_orig = row['ID_Original']
            tabla_orig = row['Tabla_Origen']

            try:
                # --- 1. CATÁLOGO, CATEGORÍA Y MARCA ---
                categoria_text = self.limpiar_dato(row['Categoria_Base']) or "GENÉRICA"
                marca_text = self.limpiar_dato(row['Marca']) or "SIN MARCA"
                modelo_text = self.limpiar_dato(row['Modelo']) or "MOD. GENÉRICO"

                cat_obj, _ = Categoria.objects.get_or_create(nombre=categoria_text.upper())
                marca_obj, _ = Marca.objects.get_or_create(nombre=marca_text.upper())
                catalogo_obj, _ = Catalogo.objects.get_or_create(
                    modelo=modelo_text.upper(), 
                    marca=marca_obj, 
                    categoria=cat_obj
                )

                # --- 2. ESTADO ---
                estado_text = self.limpiar_dato(row['Estado']) or "OPERATIVO"
                estado_obj, _ = Estado.objects.get_or_create(nombre=estado_text.upper())

                # --- 3. FUNCIONARIO ASIGNADO ---
                funcionario_obj = None
                asignado_text = self.limpiar_dato(row['Asignado_A'])
                if asignado_text:
                    funcionario_obj, _ = Funcionario.objects.get_or_create(nombre=asignado_text.upper())

                # --- 4. UBICACIÓN ---
                ubicacion_fk = None
                ubi_text = self.limpiar_dato(row['Ubicacion_Original'])
                
                if ubi_text and ubi_text.lower() != 'seleccione':
                    ubi_direct = Ubicacion.objects.filter(nombre__iexact=ubi_text).first()
                    if ubi_direct:
                        ubicacion_fk = ubi_direct
                    else:
                        try:
                            mapeo = MapeoUbicacion.objects.get(nombre_original=ubi_text)
                            if mapeo.revisado and mapeo.ubicacion_nueva:
                                ubicacion_fk = mapeo.ubicacion_nueva
                        except MapeoUbicacion.DoesNotExist:
                            pass

                # --- 5. USUARIO CREADOR ---
                # Recuperar el usuario que registró originalmente el equipo
                creador_obj = None
                creador_text = self.limpiar_dato(row.get('Creado_Por'))
                if creador_text:
                    # Creamos el usuario si no existe, o lo recuperamos
                    creador_obj, _ = User.objects.get_or_create(username=creador_text)

                # --- 6. LECTURA DE CÓDIGOS Y COLUMNAS DERIVADAS ---
                netbios = self.limpiar_dato(row['NetBios'])
                n_serie = self.limpiar_dato(row['N_Serie'])
                etiqueta = self.limpiar_dato(row['Etiqueta'])
                bdo = self.limpiar_dato(row['BDO'], solo_numeros=True)
                
                tipo_uso_asignado = row.get('Tipo_Uso', 'PER')
                tipo_red_asignado = row.get('Tipo_Red', 'OTRO')

                # --- 7. GUARDAR EL ACTIVO ---
                nuevo_activo = Activo(
                    catalogo=catalogo_obj,
                    numero_serie=n_serie,
                    etiqueta=etiqueta,
                    bdo=bdo,
                    netbios=netbios,
                    estado=estado_obj,
                    tipo_uso=tipo_uso_asignado,  
                    tipo_red=tipo_red_asignado,
                    ubicacion=ubicacion_fk,
                    asignado_a=funcionario_obj,
                    creado_por=creador_obj # <--- Asignar el usuario creador aquí
                )
                
                nuevo_activo.full_clean()
                nuevo_activo.save() # Guarda el activo, pero auto_now_add pondrá la fecha de HOY
                
                # --- 8. PRESERVAR FECHA ORIGINAL DE CREACIÓN ---
                # Usar el método .update() directamente a la BD para ignorar la regla 'auto_now_add'
                if pd.notnull(row['Fecha_Creacion']):
                    try:
                        fecha_original = pd.to_datetime(row['Fecha_Creacion'])
                        
                        # --- SOLUCIÓN PARA NAIVE DATETIMES ---
                        # Si la fecha no tiene zona horaria, se la asignamos explícitamente
                        if is_naive(fecha_original):
                            fecha_original = make_aware(fecha_original)
                            
                        Activo.objects.filter(pk=nuevo_activo.pk).update(created_at=fecha_original)
                    except:
                        pass
                
                migrados_exito += 1

            except ValidationError as e:
                self.stderr.write(self.style.ERROR(f"[Fila {index+2} - {tabla_orig} ID:{id_orig}] Validación BD: {e.message_dict}"))
                errores += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"[Fila {index+2} - {tabla_orig} ID:{id_orig}] Error crítico: {str(e)}"))
                errores += 1

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"ETL Finalizado. Activos creados exitosamente: {migrados_exito}"))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f"Filas con errores (no migradas): {errores}"))
        self.stdout.write("="*50 + "\n")