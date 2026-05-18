# adr/signals.py
from django.dispatch import receiver
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