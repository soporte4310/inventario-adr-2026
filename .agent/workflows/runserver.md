---
description: Ejecutar el servidor Django local del proyecto Inventario ADR 2026
---

# Requisitos previos

- Estar conectado a una red que permita el puerto 3306 (la red del INACAP o una red que no bloquee MySQL).
- La red local de algunos lugares bloquea el puerto 3306 — si no conecta a Clever Cloud, cambiar de red.

# Pasos

// turbo
1. Ejecutar el servidor con el Python del entorno virtual:

```
.\venv\Scripts\python manage.py runserver
```

El servidor queda disponible en http://127.0.0.1:8000

> Si aparece el error "Python was not found", significa que se usó `python` en lugar de `.\venv\Scripts\python`. Usar siempre la ruta del venv o activarlo primero con `.\venv\Scripts\Activate.ps1`.
