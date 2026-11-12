import uuid
from PIL import Image
from django.core.cache import cache
from common.utils import procesar_imagen_en_memoria, generar_thumbnail_en_memoria

# Grupos que pueden operar la revisión mensual (marcar OK, registrar
# novedades, mover equipos de sala). Sólo 'ADR' administra el roster de
# equipos y la estructura de Edificios/Pisos.
#
# Los nombres deben calzar EXACTO con los grupos reales de la base de datos
# (Group.objects...). Ojo: son los mismos que usa 'inventario' en sus vistas
# (ver inventario/views.py DashboardInventario.group_required), así que si
# esa lista cambia, hay que actualizar ésta también.
GRUPOS_REVISION = ['ADR', 'Alumno en Práctica', 'Auxiliar Operador ADR', 'Operador ADR']
GRUPOS_ADMIN = ['ADR']


def limite_alcanzado(request, accion, max_intentos=30, ventana_segundos=60):
    """
    Throttle simple basado en caché para los endpoints de escritura (marcar
    OK / subir evidencia): evita que un usuario spamee el formulario en un
    lapso corto. Usa el mismo mecanismo (django.core.cache) que ya emplea el
    bloqueo de intentos de login del proyecto, sin sumar dependencias nuevas.

    La clave combina usuario + IP (no solo uno de los dos): así no se
    bloquea a todo un equipo/red detrás de NAT que comparte la misma IP,
    pero una sesión robada desde otra IP tampoco hereda el contador de otro.
    """
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
    clave = f"mantencion_rl:{accion}:{request.user.pk}:{ip}"
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




def procesar_miniatura_revision_sala(instance, image_file, prefix="evidencia"):
    """
    Procesa el primer frame extraído del video y genera:
    1. Imagen principal optimizada (max 1024x1024) -> imagen_evidencia
    2. Miniatura mediana (600x600) -> imagen_thumb_medium
    3. Miniatura pequeña (80x80 / 50x50) -> imagen_thumb_small
    Utiliza las rutinas en memoria ya existentes en el sistema.
    """
    if not image_file:
        return

    ext = ".jpg"
    uuid_str = str(uuid.uuid4())
    base_name = f"{prefix}_{uuid_str}"

    main_name = f"{base_name}{ext}"
    med_name = f"{base_name}_medium{ext}"
    small_name = f"{base_name}_small{ext}"

    # 1. Imagen Principal
    processed_main = procesar_imagen_en_memoria(
        image_field=image_file,
        max_dimensions=(1024, 1024),
        new_filename=main_name,
        crop_to_square=False
    )
    instance.imagen_evidencia = processed_main

    # 2. Thumbnails Medium y Small
    image_file.seek(0)
    with Image.open(image_file) as img_obj:
        if hasattr(instance, "imagen_thumb_medium"):
            thumb_med = generar_thumbnail_en_memoria(
                image_obj=img_obj,
                dimensions=(600, 600),
                new_filename=med_name
            )
            instance.imagen_thumb_medium = thumb_med

        if hasattr(instance, "imagen_thumb_small"):
            thumb_small = generar_thumbnail_en_memoria(
                image_obj=img_obj,
                dimensions=(80, 80),
                new_filename=small_name
            )
            instance.imagen_thumb_small = thumb_small