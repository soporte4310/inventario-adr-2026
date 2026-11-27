import calendar
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from inventario.models import Activo, ActivoImpresora, Ubicacion
from .models import CicloRevision, RevisionSala, RevisionImpresora, RegistroActividadMantencion

MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def _poblar_revisiones_salas(ciclo):
    """
    Inserta masivamente los registros de RevisionSala para todas las
    ubicaciones con tipo SALA_CLASES o LABORATORIO y aplica_mantenimiento=True,
    vinculando su proyector actual en una única consulta optimizada.
    """
    ubicaciones = Ubicacion.objects.filter(
        tipo__in=[
            Ubicacion.TipoUbicacion.SALA_CLASES,
            Ubicacion.TipoUbicacion.LABORATORIO
        ],
        aplica_mantenimiento=True
    ).order_by('nombre')

    proyectores = Activo.objects.filter(
        ubicacion__in=ubicaciones,
        catalogo__categoria__nombre__iexact="PROYECTOR",
        is_deleted=False
    ).select_related('ubicacion', 'catalogo', 'catalogo__marca')

    mapa_proyectores = {p.ubicacion_id: p for p in proyectores}

    revisiones_a_crear = [
        RevisionSala(
            ciclo=ciclo,
            ubicacion=ubicacion,
            proyector=mapa_proyectores.get(ubicacion.id),
            estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE
        )
        for ubicacion in ubicaciones
    ]

    RevisionSala.objects.bulk_create(revisiones_a_crear)
    return len(revisiones_a_crear)


def crear_ciclo_mensual_salas(forzar=False):
    """
    Crea y abre de forma automática el ciclo del mes en curso y puebla
    las salas con aplica_mantenimiento=True y tipo='SALA_CLASES'.
    """
    hoy = timezone.localdate()
    mes_nombre = MESES_ES[hoy.month]
    nombre_ciclo = f"Revisión Salas de Clases - {mes_nombre} {hoy.year}"

    ciclo_existente = CicloRevision.objects.filter(
        tipo=CicloRevision.TipoCiclo.SALAS,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month
    ).first()

    if ciclo_existente and not forzar:
        return False, f"El ciclo '{ciclo_existente.nombre}' ya existe y está {ciclo_existente.get_estado_display()}."

    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    fecha_limite = hoy.replace(day=ultimo_dia)

    with transaction.atomic():
        ciclo = CicloRevision.objects.create(
            nombre=nombre_ciclo,
            tipo=CicloRevision.TipoCiclo.SALAS,
            estado=CicloRevision.EstadoCiclo.EN_CURSO,
            fecha_inicio=hoy,
            fecha_limite=fecha_limite,
            creado_por=None
        )
        total_pobladas = _poblar_revisiones_salas(ciclo)

    return True, f"Ciclo '{nombre_ciclo}' creado exitosamente con {total_pobladas} salas."


def crear_ciclo_extraordinario_salas(usuario, nombre_personalizado=None):
    """
    Crea un ciclo extraordinario manual para el mes actual.
    Regla de negocio: No se puede crear si ya existe un ciclo de salas
    vigente (EN_CURSO) en el mes actual.
    """
    hoy = timezone.localdate()
    mes_nombre = MESES_ES[hoy.month]

    # Validación: Verificar si existe un ciclo de salas EN_CURSO en el mes
    ciclo_vigente = CicloRevision.objects.filter(
        tipo=CicloRevision.TipoCiclo.SALAS,
        estado=CicloRevision.EstadoCiclo.EN_CURSO,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month
    ).first()

    if ciclo_vigente:
        return False, f"No es posible crear un ciclo extraordinario: el ciclo '{ciclo_vigente.nombre}' aún se encuentra en curso.", None

    # Numeración en caso de que existan otros extraordinarios finalizados este mes
    conteo_extraordinarios = CicloRevision.objects.filter(
        tipo=CicloRevision.TipoCiclo.SALAS,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month,
        nombre__icontains="Extraordinaria"
    ).count()

    sufijo = f" #{conteo_extraordinarios + 1}" if conteo_extraordinarios > 0 else ""
    nombre = nombre_personalizado.strip() if nombre_personalizado else f"Revisión Extraordinaria Salas - {mes_nombre} {hoy.year}{sufijo}"

    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    fecha_limite = hoy.replace(day=ultimo_dia)

    with transaction.atomic():
        ciclo = CicloRevision.objects.create(
            nombre=nombre,
            tipo=CicloRevision.TipoCiclo.SALAS,
            estado=CicloRevision.EstadoCiclo.EN_CURSO,
            fecha_inicio=hoy,
            fecha_limite=fecha_limite,
            creado_por=usuario
        )
        total_salas = _poblar_revisiones_salas(ciclo)

    return True, f"Ciclo extraordinario '{ciclo.nombre}' creado exitosamente con {total_salas} salas.", ciclo




# ==============================================================================
# SECCIÓN 2: REVISIONES DE IMPRESORAS
# ==============================================================================

def _poblar_revisiones_impresoras(ciclo):
    """
    Inserta masivamente los registros de RevisionImpresora para todas las
    impresoras activas que no se encuentren dadas de baja en el inventario.
    """
    impresoras = ActivoImpresora.objects.filter(
        activo__is_deleted=False
    ).exclude(
        activo__estado__nombre__icontains='BAJA'
    ).select_related('activo', 'activo__ubicacion', 'activo__catalogo')

    revisiones_a_crear = [
        RevisionImpresora(
            ciclo=ciclo,
            impresora=impresora,
            estado_general=RevisionImpresora.EstadoGeneral.PENDIENTE
        )
        for impresora in impresoras
    ]

    RevisionImpresora.objects.bulk_create(revisiones_a_crear)
    return len(revisiones_a_crear)


def crear_ciclo_mensual_impresoras(forzar=False):
    """
    Crea y abre de forma automática el ciclo mensual de impresoras del mes
    en curso y puebla todas las impresoras activas.
    """
    hoy = timezone.localdate()
    mes_nombre = MESES_ES[hoy.month]
    nombre_ciclo = f"Revisión Impresoras - {mes_nombre} {hoy.year}"

    ciclo_existente = CicloRevision.objects.filter(
        tipo=CicloRevision.TipoCiclo.IMPRESORAS,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month
    ).first()

    if ciclo_existente and not forzar:
        return False, f"El ciclo '{ciclo_existente.nombre}' ya existe y está {ciclo_existente.get_estado_display()}."

    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    fecha_limite = hoy.replace(day=ultimo_dia)

    with transaction.atomic():
        ciclo = CicloRevision.objects.create(
            nombre=nombre_ciclo,
            tipo=CicloRevision.TipoCiclo.IMPRESORAS,
            estado=CicloRevision.EstadoCiclo.EN_CURSO,
            fecha_inicio=hoy,
            fecha_limite=fecha_limite,
            creado_por=None
        )
        total_pobladas = _poblar_revisiones_impresoras(ciclo)

    return True, f"Ciclo '{nombre_ciclo}' creado exitosamente con {total_pobladas} impresoras."


def crear_ciclo_extraordinario_impresoras(usuario, nombre_personalizado=None):
    """
    Crea un ciclo extraordinario manual de impresoras para el mes actual.
    Regla de negocio: No se puede crear si ya existe un ciclo de impresoras
    vigente (EN_CURSO) en el mes actual.
    """
    hoy = timezone.localdate()
    mes_nombre = MESES_ES[hoy.month]

    ciclo_vigente = CicloRevision.objects.filter(
        tipo=CicloRevision.TipoCiclo.IMPRESORAS,
        estado=CicloRevision.EstadoCiclo.EN_CURSO,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month
    ).first()

    if ciclo_vigente:
        return False, f"No es posible crear un ciclo extraordinario: el ciclo '{ciclo_vigente.nombre}' aún se encuentra en curso.", None

    conteo_extraordinarios = CicloRevision.objects.filter(
        tipo=CicloRevision.TipoCiclo.IMPRESORAS,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month,
        nombre__icontains="Extraordinaria"
    ).count()

    sufijo = f" #{conteo_extraordinarios + 1}" if conteo_extraordinarios > 0 else ""
    nombre = nombre_personalizado.strip() if nombre_personalizado else f"Revisión Extraordinaria Impresoras - {mes_nombre} {hoy.year}{sufijo}"

    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    fecha_limite = hoy.replace(day=ultimo_dia)

    with transaction.atomic():
        ciclo = CicloRevision.objects.create(
            nombre=nombre,
            tipo=CicloRevision.TipoCiclo.IMPRESORAS,
            estado=CicloRevision.EstadoCiclo.EN_CURSO,
            fecha_inicio=hoy,
            fecha_limite=fecha_limite,
            creado_por=usuario
        )
        total_impresoras = _poblar_revisiones_impresoras(ciclo)

    return True, f"Ciclo extraordinario '{ciclo.nombre}' creado exitosamente con {total_impresoras} impresoras.", ciclo




def registrar_log_actividad(
    usuario,
    ciclo,
    tipo_revision,
    item_nombre,
    estado_resultado,
    accion,
    ubicacion_texto="",
    observaciones="",
    revision_sala=None,
    revision_impresora=None
):
    """
    Crea una entrada en la bitácora de actividad de mantención.
    """
    return RegistroActividadMantencion.objects.create(
        usuario=usuario,
        ciclo=ciclo,
        tipo_revision=tipo_revision,
        accion=accion,
        item_nombre=item_nombre,
        ubicacion_texto=ubicacion_texto,
        estado_resultado=estado_resultado,
        observaciones=observaciones,
        revision_sala=revision_sala,
        revision_impresora=revision_impresora
    )