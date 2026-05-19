from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings

from .models import LoginAttempt


UserModel = get_user_model()

class CustomAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            try:
                user = UserModel._default_manager.get(username=username)
            except UserModel.DoesNotExist:
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )

            login_attempt, created = LoginAttempt.objects.get_or_create(user=user)

            if login_attempt.is_locked():
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
                login_attempt.reset_attempts()
                self.user_cache = user_autenticado
        
        return self.cleaned_data