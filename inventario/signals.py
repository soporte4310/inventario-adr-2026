from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from adr.middleware import get_current_user
from .models import Activo, AuditoriaActivo


@receiver(pre_save, sender=Activo)
def auditoria_pre_save_activo(sender, instance, **kwargs):
    """Detecta modificaciones y eliminaciones antes de guardar."""
    if not instance.pk:
        return # Es una creación, se maneja en post_save

    try:
        viejo_activo = Activo.objects.get(pk=instance.pk)
    except Activo.DoesNotExist:
        return

    user = get_current_user()
    ct = ContentType.objects.get_for_model(instance)

    # 1. Detección de Soft Delete (Eliminación)
    if not viejo_activo.is_deleted and instance.is_deleted:
        AuditoriaActivo.objects.create(
            usuario=user,
            accion=AuditoriaActivo.TipoAccion.ELIMINACION,
            content_type=ct,
            object_id=instance.pk,
            valor_anterior="Activo en Inventario",
            valor_nuevo="Movido a Eliminados"
        )
        return

    # 2. Comparación de campos para Modificación
    # Excluimos campos de sistema como la fecha de actualización
    campos_obviar = ['updated_at', 'created_at']
    
    for field in instance._meta.fields:
        if field.name in campos_obviar:
            continue

        v_anterior = getattr(viejo_activo, field.name)
        v_nuevo = getattr(instance, field.name)

        if v_anterior != v_nuevo:
            # Mejora: Si es una relación (FK), mostramos el nombre, no el ID
            if field.is_relation and v_anterior:
                v_anterior = str(v_anterior)
                v_nuevo = str(v_nuevo) if v_nuevo else "Ninguno"

            AuditoriaActivo.objects.create(
                usuario=user,
                accion=AuditoriaActivo.TipoAccion.MODIFICACION,
                content_type=ct,
                object_id=instance.pk,
                campo=field.verbose_name,
                valor_anterior=str(v_anterior) if v_anterior is not None else "Vacío",
                valor_nuevo=str(v_nuevo) if v_nuevo is not None else "Vacío"
            )

@receiver(post_save, sender=Activo)
def auditoria_post_save_activo(sender, instance, created, **kwargs):
    """Registra la creación inicial del activo."""
    if created:
        AuditoriaActivo.objects.create(
            usuario=get_current_user(),
            accion=AuditoriaActivo.TipoAccion.CREACION,
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            valor_nuevo=f"Registro inicial de {instance.catalogo}"
        )