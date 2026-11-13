import calendar
from django.db import transaction
from django.utils import timezone
from inventario.models import Activo, Ubicacion
from .models import CicloRevision, RevisionSala

MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def _poblar_revisiones_salas(ciclo):
    """
    Inserta masivamente los registros de RevisionSala para todas las
    ubicaciones con tipo SALA_CLASES y aplica_mantenimiento=True,
    vinculando su proyector actual en una única consulta optimizada.
    """
    ubicaciones = Ubicacion.objects.filter(
        tipo=Ubicacion.TipoUbicacion.SALA_CLASES,
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