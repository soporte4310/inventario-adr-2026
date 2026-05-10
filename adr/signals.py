# adr/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from adr.models import (
    HistorialCambios, AllInOne, Notebook, MiniPC, Proyectores,
    BodegaADR, Azotea, AllInOneAdmins, EquiposIsla, SwitchDeRed,
    Monitor, Audio, Tablet, Televisor,
)
from accounts.models import Profile
from adr.middleware import get_current_user

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.dispatch import receiver


# ---------------------------------------------------------------------
# 1) HISTORIAL DE CAMBIOS
# ---------------------------------------------------------------------
@receiver(pre_save, sender=AllInOne)
@receiver(pre_save, sender=AllInOneAdmins)
@receiver(pre_save, sender=Notebook)
@receiver(pre_save, sender=MiniPC)
@receiver(pre_save, sender=Proyectores)
@receiver(pre_save, sender=BodegaADR)
@receiver(pre_save, sender=Azotea)
@receiver(pre_save, sender=EquiposIsla)
@receiver(pre_save, sender=SwitchDeRed)
@receiver(pre_save, sender=Monitor)
@receiver(pre_save, sender=Audio)
@receiver(pre_save, sender=Tablet)
@receiver(pre_save, sender=Televisor)
def registrar_cambios(sender, instance, **kwargs):
    try:
        original_instance = sender.objects.get(pk=instance.pk)

        for field in instance._meta.fields:
            field_name = field.name
            old_value = getattr(original_instance, field_name, None)
            new_value = getattr(instance, field_name, None)

            if old_value != new_value:
                HistorialCambios.objects.create(
                    modelo=sender.__name__,
                    objeto_id=instance.pk,
                    usuario=get_current_user(),
                    campo_modificado=field.verbose_name,
                    valor_anterior=old_value if old_value is not None else "N/A",
                    valor_nuevo=new_value if new_value is not None else "N/A",
                )
    except sender.DoesNotExist:
        HistorialCambios.objects.create(
            modelo=sender.__name__,
            objeto_id=instance.pk,
            usuario=get_current_user(),
            campo_modificado="Creación",
            valor_anterior="N/A",
            valor_nuevo=str(instance),
        )

# ---------------------------------------------------------------------
# 2) ALERTA Y BLOQUEO EN LOGIN
# ---------------------------------------------------------------------
def _key(username=None, ip=None):
    return f"login_failed_ip:{ip or 'unknown'}"

def _alert_key(username=None, ip=None):
    return f"login_failed_alert_sent:{username or 'unknown'}:{ip or 'unknown'}"

def _lock_key(username=None, ip=None):
    return f"login_lock_ip:{ip or 'unknown'}"
LOCK_SECONDS = getattr(settings, "LOGIN_LOCK_SECONDS", 60)

def _extract_username(credentials, request):
    """
    Obtiene el username intentando en este orden:
    - credentials[USERNAME_FIELD]
    - request.POST[USERNAME_FIELD]
    - request.POST['username'] (por si el input HTML se llama 'username')
    """
    User = get_user_model()
    uname_field = getattr(User, "USERNAME_FIELD", "username")

    val = None
    if credentials:
        val = credentials.get(uname_field) or credentials.get("username")
    if not val and request is not None:
        val = request.POST.get(uname_field) or request.POST.get("username")
    return (val or "").strip().lower()  # normaliza

@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    ip  = request.META.get('REMOTE_ADDR') if request else None
    ua  = request.META.get('HTTP_USER_AGENT', '') if request else ''
    username = _extract_username(credentials, request)

    # contador
    key   = _key(username, ip)
    count = cache.get(key, 0) + 1
    cache.set(key, count, timeout=getattr(settings, "LOGIN_FAILED_WINDOW_SECONDS", 900))

    # umbral -> lock + (correo 1 vez por ventana)
    if count >= getattr(settings, "LOGIN_FAILED_THRESHOLD", 3):
        lock_until = timezone.now() + timedelta(seconds=LOCK_SECONDS)
        cache.set(_lock_key(username, ip), lock_until.isoformat(), timeout=LOCK_SECONDS)

        sent_key = _alert_key(username, ip)
        if not cache.get(sent_key):
            from adr.email_template import notificacion_alerta_login

            now = timezone.now().strftime("%d/%m/%Y %H:%M:%S")
            html, plain = notificacion_alerta_login(
                intentos=count,
                username=username,
                ip=ip,
                user_agent=ua,
                fecha=now,
            )

            from adr.utils import enviar_notificacion_asunto
            enviar_notificacion_asunto(
                asunto="ALERTA: 3 intentos fallidos de inicio de sesión",
                mensaje=plain,
                destinatarios=getattr(settings, "EMAIL_RECIPIENTS", []),
                html_content=html,
            )
            cache.set(sent_key, True, timeout=getattr(settings, "LOGIN_FAILED_WINDOW_SECONDS", 900))

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR') if request else None
    # usa el USERNAME_FIELD real del usuario
    username = (getattr(user, getattr(user.__class__, "USERNAME_FIELD", "username"), None) 
                or user.get_username())
    username = (username or "").strip().lower()
    cache.delete(_key(username, ip))
    cache.delete(_alert_key(username, ip))
    cache.delete(_lock_key(username, ip))