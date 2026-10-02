from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings

from .models import LoginAttempt, RegistroAcceso


UserModel = get_user_model()

class CustomAuthenticationForm(AuthenticationForm):
    def _portal_actual(self):
        # Inventario y Mantención comparten este mismo formulario; se
        # distingue por el path de la URL que originó el POST.
        path = self.request.path if self.request else ''
        return RegistroAcceso.Portal.MANTENCION if path.startswith('/mantencion/') else RegistroAcceso.Portal.INVENTARIO

    def _ip_actual(self):
        if not self.request:
            return None
        # Render reenvía la IP real del visitante en X-Forwarded-For; sin
        # eso, REMOTE_ADDR sería la IP interna del proxy, no la del usuario.
        adelante = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if adelante:
            return adelante.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _registrar_acceso(self, username, resultado, usuario=None):
        RegistroAcceso.objects.create(
            usuario=usuario, username_ingresado=username or '', resultado=resultado,
            portal=self._portal_actual(), ip=self._ip_actual(),
        )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            try:
                user = UserModel._default_manager.get(username=username)
            except UserModel.DoesNotExist:
                self._registrar_acceso(username, RegistroAcceso.Resultado.USUARIO_INEXISTENTE)
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )

            # Cuenta desactivada por ADR: se corta aquí, ANTES de contar como intento fallido
            # (si no, el usuario vería "contraseña incorrecta" y se ganaría bloqueos injustos).
            if not user.is_active:
                self._registrar_acceso(username, RegistroAcceso.Resultado.CUENTA_DESACTIVADA, usuario=user)
                raise ValidationError(
                    'Esta cuenta ha sido desactivada. Contacte al administrador.',
                    code='inactive',
                )

            login_attempt, created = LoginAttempt.objects.get_or_create(user=user)

            if login_attempt.is_locked():
                self._registrar_acceso(username, RegistroAcceso.Resultado.CUENTA_BLOQUEADA, usuario=user)
                lockout_time_left = login_attempt.lockout_until - timezone.now()
                minutes_left = int(lockout_time_left.total_seconds() // 60)
                seconds_left = int(lockout_time_left.total_seconds() % 60)

                raise ValidationError(
                    f"Su cuenta ha sido bloqueada temporalmente debido a múltiples intentos fallidos. "
                    f"Por favor, inténtelo de nuevo en {minutes_left} minutos y {seconds_left} segundos.",
                    code='account_locked',
                )

            user_autenticado = authenticate(username=username, password=password)

            if user_autenticado is None:
                self._registrar_acceso(username, RegistroAcceso.Resultado.CONTRASENA_INCORRECTA, usuario=user)
                login_attempt.increment_failed_attempts()
                
                # INTEGRACIÓN: Envío de correo electrónico al segundo intento fallido
                if login_attempt.failed_attempts == 2:
                    try:
                        subject = f"[Alerta] 2 intentos fallidos de {username}"
                        # Extraemos la IP del cliente usando el objeto request guardado nativamente por el formulario
                        ip_address = self.request.META.get('REMOTE_ADDR') if self.request else 'Desconocida'
                        body = (
                            f"Usuario: {username}\n"
                            f"IP: {ip_address}\n"
                            f"Hora: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            "Se han registrado 2 intentos fallidos de inicio de sesión."
                        )
                        send_mail(
                            subject,
                            body,
                            settings.DEFAULT_FROM_EMAIL,
                            getattr(settings, 'EMAIL_RECIPIENTS', []),
                            fail_silently=False,
                        )
                    except Exception as email_err:
                        # Evita que un fallo de configuración SMTP (ej. sin internet o credenciales de correo malas) 
                        # rompa el flujo de la aplicación.
                        print(f"[ERROR SMTP] No se pudo enviar el correo de alerta: {str(email_err)}")

                if login_attempt.is_locked():
                    lockout_time_left = login_attempt.lockout_until - timezone.now()
                    minutes_left = int(lockout_time_left.total_seconds() // 60)
                    seconds_left = int(lockout_time_left.total_seconds() % 60)
                    raise ValidationError(
                        f"Credenciales incorrectas. Su cuenta ha sido bloqueada temporalmente por 5 minutos.",
                        code='account_locked_now',
                    )
                else:
                    remaining_attempts = 3 - login_attempt.failed_attempts
                    if login_attempt.failed_attempts == 2:
                        raise ValidationError(
                            "Contraseña incorrecta. Se ha enviado un aviso al equipo de seguridad. Le queda 1 intento.",
                            code='invalid_login_warning_email',
                        )
                    else:
                        raise ValidationError(
                            f"Credenciales incorrectas. Le quedan {remaining_attempts} intentos.",
                            code='invalid_login_attempts_left',
                        )
            else:
                self._registrar_acceso(username, RegistroAcceso.Resultado.EXITOSO, usuario=user)
                login_attempt.reset_attempts()
                self.user_cache = user_autenticado

        return self.cleaned_data