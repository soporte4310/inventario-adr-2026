from django.db import transaction
from .models import Categoria, Marca, Catalogo, Activo
import pandas as pd


def fusionar_categorias(nombre_correcto, nombre_incorrecto):
    """Mueve todos los catálogos de una categoría mala a la buena y elimina la mala."""
    try:
        with transaction.atomic():
            cat_correcta = Categoria.objects.get(nombre__iexact=nombre_correcto)
            cat_mala = Categoria.objects.get(nombre__iexact=nombre_incorrecto)
            
            # Buscamos todos los catálogos que usan la categoría mala
            catalogos = Catalogo.objects.filter(categoria=cat_mala)
            cantidad = catalogos.count()
            
            # Reasignamos masivamente
            catalogos.update(categoria=cat_correcta)
            
            # Ahora que no tiene catálogos dependientes, la podemos borrar
            cat_mala.delete()
            print(f"Éxito: {cantidad} catálogos movidos de '{nombre_incorrecto}' a '{nombre_correcto}'. Categoría eliminada.")
    except Exception as e:
        print(f"Error: {e}")


def fusionar_marcas(nombre_correcto, nombre_incorrecto):
    """Mueve todos los catálogos de una marca mal escrita a la correcta y la elimina."""
    try:
        with transaction.atomic():
            marca_correcta = Marca.objects.get(nombre__iexact=nombre_correcto)
            marca_mala = Marca.objects.get(nombre__iexact=nombre_incorrecto)
            
            catalogos = Catalogo.objects.filter(marca=marca_mala)
            cantidad = catalogos.count()
            
            catalogos.update(marca=marca_correcta)
            marca_mala.delete()
            print(f"Éxito: {cantidad} catálogos movidos de '{nombre_incorrecto}' a '{nombre_correcto}'. Marca eliminada.")
    except Exception as e:
        print(f"Error: {e}")


def _get_excel_val(row, column_name, default=None, to_upper=False):
    """
    Función auxiliar para extraer valores de Pandas de forma segura.
    Evita que las celdas vacías de Excel se conviertan en el string "None".
    """
    val = row.get(column_name)
    if pd.isna(val) or val is None:
        return default
    
    val_str = str(val).strip()
    if val_str.upper() in ['NONE', 'NAN', 'NULL', '']:
        return default
        
    return val_str.upper() if to_upper else val_str