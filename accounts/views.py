from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

from .forms import CustomAuthenticationForm
from .models import LoginAttempt
from adr.decorators import add_group_name_to_context

User = get_user_model()


#class CustomLoginView(LoginView):
#    authentication_form = CustomAuthenticationForm
#    template_name = 'registration/login.html'
#
#    def form_invalid(self, form):
#        username = form.cleaned_data.get('username')
#        if username:
#            try:
#                user = User.objects.get(username=username)
#                login_attempt, _ = LoginAttempt.objects.get_or_create(user=user)
#
#                if login_attempt.is_locked():
#                    messages.error(self.request, "Tu cuenta está bloqueada. Inténtalo de nuevo más tarde.")
#                    return super().form_invalid(form)
#
#                login_attempt.increment_failed_attempts()
#
#                if login_attempt.failed_attempts == 2:
#                    subject = f"[Alerta] 2 intentos fallidos de {username}"
#                    body = (
#                        f"Usuario: {username}\n"
#                        f"IP: {self.request.META.get('REMOTE_ADDR')}\n"
#                        f"Hora: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
#                        "Se han registrado 2 intentos fallidos de inicio de sesión."
#                    )
#                    send_mail(
#                        subject,
#                        body,
#                        settings.DEFAULT_FROM_EMAIL,
#                        getattr(settings, 'EMAIL_RECIPIENTS', []),
#                        fail_silently=False,
#                    )
#                    messages.warning(
#                        self.request,
#                        "Contraseña incorrecta. Se ha enviado un aviso al equipo de seguridad."
#                    )
#
#                if login_attempt.is_locked():
#                    messages.error(
#                        self.request,
#                        "Demasiados intentos fallidos. Tu cuenta ha sido bloqueada por 5 minutos."
#                    )
#                elif login_attempt.failed_attempts == 1:
#                    messages.error(self.request, "Contraseña incorrecta.")
#
#            except User.DoesNotExist:
#                messages.error(self.request, "Usuario o contraseña incorrectos.")
#            except Exception:
#                messages.error(self.request, "Ocurrió un error durante el inicio de sesión.")
#
#        return super().form_invalid(form)




@add_group_name_to_context
class CustomLoginView(LoginView):
    redirect_authenticated_user = True
    
    def form_invalid(self, form):
        messages.error(self.request, 'Usuario o contraseña incorrectos. Por favor, intente nuevamente.')
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()
        profile = getattr(user, "profile", None)

        if profile and profile.create_by_adr:
            messages.warning(self.request, 'Bienvenido, debes cambiar tu contraseña ahora.')
            return HttpResponseRedirect(reverse_lazy('profile_password_change'))

        resp = super().form_valid(form)
        messages.success(self.request, 'Inicio de sesión exitoso.')
        return resp