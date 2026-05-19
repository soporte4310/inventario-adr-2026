"""
Paquete de vistas del módulo ADR.

Este paquete organiza las vistas en módulos especializados:
- base: Vistas genéricas reutilizables
- equipos: CRUD de equipos refactorizados (TODOS los modelos)
- delete: Vistas de eliminación lógica y gestión de eliminados
- historial: Vistas de historial de cambios
- auth: Vistas de autenticación y perfil de usuario
- excel: Vistas de descarga de datos en Excel
- views_legacy: Archivo original (temporalmente para backward compatibility)

ESTRATEGIA INCREMENTAL:
1. Importamos TODAS las vistas del archivo legacy
2. Sobrescribimos con las vistas refactorizadas
3. urls.py sigue funcionando sin cambios
"""

# Importar vistas restantes (upload, users, utils) de views_other
# NOTA: Este archivo contiene vistas especializadas aún no refactorizadas
from adr.views_other import *

# Sobrescribir vistas de autenticación y perfil
from .auth import (
    my_profile,
    UserPasswordChangeView,
    CustomPasswordResetView,
)