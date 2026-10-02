from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import ListView

from .forms import CustomAuthenticationForm
from .mixins import GroupRequiredMixin
from .models import LoginAttempt, Profile, RegistroAcceso
from adr.decorators import add_group_name_to_context

User = get_user_model()


@add_group_name_to_context
class CustomLoginView(LoginView):
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True
    
    def form_invalid(self, form):
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(self.request, error)
        else:
            messages.error(self.request, 'Usuario o contraseña incorrectos. Por favor, intente nuevamente.')
            
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()
        
        # Inicia la sesión formalmente en el navegador (creación de cookies de sesión)
        login(self.request, user)
        
        profile = getattr(user, "profile", None)

        # Si fue creado por la administración, lo forzamos a cambiar contraseña
        if profile and profile.create_by_adr:
            messages.warning(self.request, 'Bienvenido, debes cambiar tu contraseña ahora.')
            return HttpResponseRedirect(reverse_lazy('profile_password_change'))

        messages.success(self.request, 'Inicio de sesión exitoso.')
        return HttpResponseRedirect(self.get_success_url())




@add_group_name_to_context
class ProfilePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Vista para cambio de contraseña de perfil"""
    template_name = 'profiles/change_password.html'
    success_url = reverse_lazy('dashboard_inventario')

    def get_context_data(self, **kwargs):
        """Añade estado de cambio de contraseña al contexto"""
        context = super().get_context_data(**kwargs)
        context['password_changed'] = self.request.session.get('password_changed', False)
        return context
    
    def form_valid(self, form):
        """
        Procesa el cambio de contraseña exitoso
        - Actualiza el estado del perfil
        - Establece mensajes de éxito
        - Actualiza la sesión
        """
        profile = Profile.objects.get(user=self.request.user)
        profile.create_by_adr = False
        profile.save()

        messages.success(self.request, 'Contraseña cambiada exitosamente')
        update_session_auth_hash(self.request, form.user)
        self.request.session['profile_password_changed'] = True
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Manejo de formulario inválido con mensaje de error"""
        messages.error(self.request, 'Las contraseñas no coinciden o no cumple el estándar de seguridad')
        return super().form_invalid(form)


class RegistroAccesoListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    """
    Auditoría de accesos (solo ADR): quién entró, cuándo, desde qué portal
    (Inventario/Mantención) y el resultado (exitoso, contraseña incorrecta,
    cuenta desactivada/bloqueada, usuario inexistente). Solo lectura.
    """
    group_required = ['ADR']
    model = RegistroAcceso
    template_name = 'profiles/registro_accesos.html'
    context_object_name = 'registros'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().select_related('usuario')

        username = self.request.GET.get('usuario')
        if username:
            queryset = queryset.filter(username_ingresado__icontains=username)

        resultado = self.request.GET.get('resultado')
        if resultado in RegistroAcceso.Resultado.values:
            queryset = queryset.filter(resultado=resultado)

        portal = self.request.GET.get('portal')
        if portal in RegistroAcceso.Portal.values:
            queryset = queryset.filter(portal=portal)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['resultados'] = RegistroAcceso.Resultado.choices
        context['portales'] = RegistroAcceso.Portal.choices
        context['usuario_filtro'] = self.request.GET.get('usuario', '')
        context['resultado_filtro'] = self.request.GET.get('resultado', '')
        context['portal_filtro'] = self.request.GET.get('portal', '')
        return context