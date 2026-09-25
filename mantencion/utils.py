from django.core.cache import cache

# Grupos que pueden operar la revisión mensual (marcar OK, registrar
# novedades, mover equipos de sala). Sólo 'ADR' administra el roster de
# equipos y la estructura de Edificios/Pisos.
#
# Los nombres deben calzar EXACTO con los grupos reales de la base de datos
# (Group.objects...). Ojo: son los mismos que usa 'inventario' en sus vistas
# (ver inventario/views.py DashboardInventario.group_required), así que si
# esa lista cambia, hay que actualizar ésta también.
GRUPOS_REVISION = ['ADR', 'Alumnos en Práctica', 'Auxiliares Operadores ADR', 'Operadores ADR']
GRUPOS_ADMIN = ['ADR']


def limite_alcanzado(user, accion, max_intentos=30, ventana_segundos=60):
    """
    Throttle simple basado en caché para los endpoints de escritura (marcar
    OK / subir evidencia): evita que un usuario spamee el formulario en un
    lapso corto. Usa el mismo mecanismo (django.core.cache) que ya emplea el
    bloqueo de intentos de login del proyecto, sin sumar dependencias nuevas.
    """
    clave = f"mantencion_rl:{accion}:{user.pk}"
    intentos = cache.get(clave, 0)
    if intentos >= max_intentos:
        return True
    cache.set(clave, intentos + 1, ventana_segundos)
    return False


def registrar_auditoria(usuario, accion, equipo_descripcion, tipo_equipo=None, detalle=''):
    """
    Deja constancia en la bitácora de auditoría de mantención (solo lectura,
    ver AuditoriaMantencionView). 'equipo_descripcion' debe ser el snapshot
    de texto del equipo (ej. equipo.marca_modelo + su N° de serie), no una
    referencia que dependa de que el equipo siga existiendo.
    """
    from .models import RegistroAuditoria

    RegistroAuditoria.objects.create(
        usuario=usuario, accion=accion, tipo_equipo=tipo_equipo,
        equipo_descripcion=equipo_descripcion, detalle=detalle,
    )


def crear_nuevo_ciclo(tipo, usuario=None, fecha=None):
    """
    Crea un nuevo CicloRevision de 'tipo' con la fecha dada (hoy por
    defecto) y una fila RevisionEquipo 'pendiente' por cada equipo activo
    de ese tipo en el roster. La usan tanto el botón "Nuevo ciclo/revisión"
    como el comando de management, para no duplicar la lógica.

    Devuelve (ciclo, cantidad_de_equipos_agregados).
    """
    from django.utils import timezone

    from .models import CicloRevision, EquipoMantenible, Impresora, RevisionEquipo

    fecha = fecha or timezone.localdate()
    ciclo = CicloRevision.objects.create(tipo=tipo, fecha_inicio=fecha, generado_por=usuario)

    # Excluimos equipos pausados por el ADR o dados de baja: no tiene
    # sentido pedirle a un practicante que revise un equipo que ya no está
    # en servicio. Proyectores e impresoras marcan "de baja" en modelos
    # distintos (Activo.is_deleted/estado vs Impresora.estado), así que el
    # filtro se arma distinto según el tipo.
    equipos_activos = EquipoMantenible.objects.filter(tipo=tipo, activo_en_revision=True)
    if tipo == EquipoMantenible.Tipo.PROYECTOR:
        equipos_activos = equipos_activos.exclude(activo__is_deleted=True).exclude(
            activo__estado__nombre__iexact='De Baja'
        ).select_related('activo__ubicacion')
    else:
        equipos_activos = equipos_activos.exclude(
            impresora__estado=Impresora.EstadoImpresora.DE_BAJA
        ).select_related('impresora__ubicacion')

    nuevas = [
        RevisionEquipo(ciclo=ciclo, equipo=equipo, ubicacion_en_revision=equipo.ubicacion)
        for equipo in equipos_activos
    ]
    RevisionEquipo.objects.bulk_create(nuevas)

    return ciclo, len(nuevas)
