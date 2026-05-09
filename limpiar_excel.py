import pandas as pd
import numpy as np

# Script para aplicar limpieza de datos al archivo excel extraído, en el cual se reunen los datos de todos los modelos anteriores

def limpiar_excel():
    print("Cargar archivo Excel original...")
    
    # 1. Leer el Excel original
    df = pd.read_excel('activos_staging.xlsx')

    # 2. Homologar los datos vacíos
    # Convertir falsos nulos a valores nulos reales de Pandas (NaN)
    df.replace(['0', 0, 'None', 'none', 'NONE', ''], np.nan, inplace=True)
    df.replace(r'^\s*$', np.nan, regex=True, inplace=True)

    # --- 2.5 APLICAR REGLAS DE NEGOCIO Y LIMPIEZA ESPECÍFICA ---
    print("Aplicar reglas de limpieza y derivación de columnas...")
    
    # Limpiar espacios en los extremos de todas las columnas de texto
    columnas_texto = ['Categoria_Base', 'Marca', 'Estado', 'Asignado_A']
    for col in columnas_texto:
        if col in df.columns:
            df[col] = df[col].str.strip()

    # Forzar columnas a MAYÚSCULAS antes de comparar para atrapar todas las variantes
    df['Categoria_Base'] = df['Categoria_Base'].str.upper()
    df['Marca'] = df['Marca'].str.upper()
    df['Asignado_A'] = df['Asignado_A'].str.upper() # <--- Clave para atrapar "No Asignado"

    # Reemplazar valores en Categoria_Base 
    reemplazos_categoria = {
        'PANTALLA': 'MONITOR',
        'ALL_IN_ONE': 'ALL IN ONE',
        'ALL IN ONE ACADÉMICO': 'ALL IN ONE',
        'ALL IN ONE ACADEMICO': 'ALL IN ONE', 
        'ALL IN ONE ADMINISTRATIVO': 'ALL IN ONE',
        'AIO ADMIN': 'ALL IN ONE',
        'SWITCH_DE_RED': 'SWITCH DE RED',
        'TORRE PC': 'PC DE TORRE',
        'EQUIPOS_ISLA': 'ALL IN ONE',
        'IPAD 9° GEN.': 'IPAD',
        'IPAD 9° GENERACIÓN': 'IPAD',
        'IPAD 9° GENERACION': 'IPAD',
        'MULTIPART': 'MULTIPAR'
    }
    df['Categoria_Base'] = df['Categoria_Base'].replace(reemplazos_categoria)

    # Reemplazar valores en Marca y Estado
    df['Marca'] = df['Marca'].replace(['INTEL CORE', 'INTEL NUC'], 'INTEL')
    df['Estado'] = df['Estado'].replace(['Malo', 'Mala', 'MALO', 'MALA'], 'DAÑADO')
    
    # Reemplazar valores en Asignado_A (pasar a nulos reales para evitar falsos funcionarios)
    # Ahora que todo está en mayúsculas, atrapamos cualquier variación
    falsos_usuarios = ['(SIN USUARIO)', 'ACADÉMICO', 'ACADEMICO', 'NO ASIGNADO', 'NADIE', 'N/A']
    df['Asignado_A'] = df['Asignado_A'].replace(falsos_usuarios, np.nan)

    # --- NUEVA LÓGICA ETL: DERIVACIÓN DE COLUMNAS ---
    
    # Derivar Tipo_Uso
    condiciones_uso = [
        df['Tabla_Origen'] == 'AllInOneAdmins',
        df['Tabla_Origen'] == 'Audio'
    ]
    valores_uso = ['ADM', 'EVE'] # Códigos exactos (Administrativo, Eventos)
    df['Tipo_Uso'] = np.select(condiciones_uso, valores_uso, default='PER')

    # Derivar Tipo_Red
    condiciones_red = [
        df['Tabla_Origen'] == 'EquiposIsla',
        df['NetBios'].notna() # Evaluar si NetBios no es nulo
    ]
    valores_red = ['ISLA', 'DOM'] 
    df['Tipo_Red'] = np.select(condiciones_red, valores_red, default='OTRO')
    # -----------------------------------------------------------

    # 3. Crear un "Puntaje de Completitud"
    # Asignar un punto a la fila por cada dato valioso que tenga lleno
    columnas_importantes = ['BDO', 'NetBios', 'Etiqueta', 'Asignado_A', 'Ubicacion_Original']
    df['puntaje'] = df[columnas_importantes].notna().sum(axis=1)

    # 4. Ordenar y Eliminar Duplicados por N° de Serie
    # Garantizar que el duplicado más completo quede siempre primero.
    df.sort_values(by=['N_Serie', 'puntaje'], ascending=[True, False], inplace=True)
    
    # Separar los que tienen N_Serie de los que no para evitar borrar equipos sin serie
    df_con_serie = df[df['N_Serie'].notna()]
    df_sin_serie = df[df['N_Serie'].isna()]
    
    # Eliminar duplicados conservando el primero (el de mayor puntaje)
    df_con_serie_limpio = df_con_serie.drop_duplicates(subset=['N_Serie'], keep='first')

    # 5. Volver a unir la tabla
    df_final = pd.concat([df_con_serie_limpio, df_sin_serie])

    # 6. Limpiar duplicados de BDO y Etiqueta
    df_final = df_final[df_final['BDO'].isna() | ~df_final.duplicated(subset=['BDO'], keep='first')]
    df_final = df_final[df_final['Etiqueta'].isna() | ~df_final.duplicated(subset=['Etiqueta'], keep='first')]

    # 7. Ejecutar limpieza final para el Excel
    # Borrar la columna temporal de puntaje
    df_final.drop(columns=['puntaje'], inplace=True)
    
    # Restaurar los nulos a celdas vacías para mantener el Excel limpio
    df_final.fillna('', inplace=True)

    # 8. Guardar el nuevo Excel inmaculado
    df_final.to_excel('activos_staging_limpio.xlsx', index=False)
    print("¡Finalizar limpieza! Revisar el nuevo archivo 'activos_staging_limpio.xlsx'")

if __name__ == '__main__':
    limpiar_excel()