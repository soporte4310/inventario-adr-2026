# mantencion/services.py
import calendar
from django.db import transaction
from django.utils import timezone
from inventario.models import Activo, Ubicacion
from .models import CicloRevision, RevisionSala

MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def crear_ciclo_mensual_salas(forzar=False):
    """
    Crea y abre de forma automática el ciclo del mes en curso y puebla
    las salas con aplica_mantenimiento=True y tipo='SALA_CLASES'.
    """
    hoy = timezone.localdate()
    mes_nombre = MESES_ES[hoy.month]
    nombre_ciclo = f"Revisión Salas de Clases - {mes_nombre} {hoy.year}"

    # 1. Idempotencia: Verificar si ya existe un ciclo para este mes y año
    ciclo_existente = CicloRevision.objects.filter(
        tipo=CicloRevision.TipoCiclo.SALAS,
        fecha_inicio__year=hoy.year,
        fecha_inicio__month=hoy.month
    ).first()

    if ciclo_existente and not forzar:
        return False, f"El ciclo '{ciclo_existente.nombre}' ya existe y está {ciclo_existente.get_estado_display()}."

    # 2. Calcular último día del mes para la fecha límite
    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    fecha_limite = hoy.replace(day=ultimo_dia)

    with transaction.atomic():
        # Crear ciclo abierto
        ciclo = CicloRevision.objects.create(
            nombre=nombre_ciclo,
            tipo=CicloRevision.TipoCiclo.SALAS,
            estado=CicloRevision.EstadoCiclo.EN_CURSO,
            fecha_inicio=hoy,
            fecha_limite=fecha_limite,
            creado_por=None  # Indicar None para identificar ejecución automática del sistema
        )

        # 3. Filtrar ubicaciones requeridas
        ubicaciones = Ubicacion.objects.filter(
            tipo=Ubicacion.TipoUbicacion.SALA_CLASES,
            aplica_mantenimiento=True
        ).order_by('nombre')

        # 4. Optimización SQL: Mapear proyectores en 1 sola consulta
        proyectores = Activo.objects.filter(
            ubicacion__in=ubicaciones,
            catalogo__categoria__nombre__iexact="PROYECTOR",
            is_deleted=False
        ).select_related('ubicacion', 'catalogo', 'catalogo__marca')

        # Diccionario {ubicacion_id: proyector}
        mapa_proyectores = {p.ubicacion_id: p for p in proyectores}

        # 5. Armar registros en memoria
        revisiones_a_crear = []
        for ubicacion in ubicaciones:
            revisiones_a_crear.append(
                RevisionSala(
                    ciclo=ciclo,
                    ubicacion=ubicacion,
                    proyector=mapa_proyectores.get(ubicacion.id),
                    estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE
                )
            )

        # 6. Inserción masiva única
        RevisionSala.objects.bulk_create(revisiones_a_crear)

    return True, f"Ciclo '{nombre_ciclo}' creado exitosamente con {len(revisiones_a_crear)} salas."