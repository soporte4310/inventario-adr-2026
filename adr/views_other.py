"""
views.py - Archivo principal de vistas de la aplicación
Contiene todas las vistas para manejar las diferentes funcionalidades del sistema
"""

import os

from django.db.models import Q, F
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import ListView, TemplateView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.utils.crypto import get_random_string

from accounts.models import Profile
from adr.utils import enviar_notificacion_asunto
from .decorators import add_group_name_to_context, get_group_and_color
from .forms import (
    LoginForm, ProfileForm, UserForm, RegisterUserForm,
    ProfileImageForm, UserUpdateForm,PrestamoForm,
)
from .models import (
    Prestamo,
)
from .funciones import enviar_correo_activacion_nuevo_usuario


@login_required
def my_profile(request):
    user = request.user
    profile = user.profile

    uform = UserUpdateForm(instance=user)
    pform = ProfileImageForm(instance=profile)

    if request.method == "POST":
        # 1) Guardar datos
        if "save_user" in request.POST:
            uform = UserUpdateForm(request.POST, instance=user)
            if uform.is_valid():
                uform.save()
                messages.success(request, "Datos actualizados correctamente.")
                return redirect("my_profile")
            else:
                messages.error(request, "Revisa los campos del formulario.")

        # 2) Guardar foto
        elif "save_photo" in request.POST:
            pform = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if pform.is_valid():
                try:
                    pform.save()
                    messages.success(request, "Tu foto de perfil fue actualizada.")
                    return redirect("my_profile")
                except Exception as e:
                    # Log detallado del error para diagnóstico
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al guardar foto de perfil: {str(e)}", exc_info=True)
                    messages.error(request, f"Error al subir la foto: {str(e)}")
            else:
                messages.error(request, "No se pudo actualizar la foto. Revisa el archivo.")

        # 3) **ELIMINAR foto**  <-- Faltaba esto
        elif "delete_image" in request.POST:
            if profile.image:
                # borra el archivo del disco y limpia el campo
                profile.image.delete(save=False)
                profile.image = None
                profile.save()
                messages.success(request, "La foto de perfil fue eliminada.")
            else:
                messages.info(request, "No tenías una foto subida.")
            return redirect("my_profile")

    group = request.user.groups.first().name if request.user.groups.exists() else "Invitado"

    return render(
        request,
        "profiles/my_profile.html",
        {
            "user_form": uform,
            "photo_form": pform,
            "user_profile": user,
            "group_name_singular": group,
        },
    )

class UserPasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    template_name = "profiles/password_change.html"
    success_url = reverse_lazy("my_profile")
    success_message = "Tu contraseña se cambió correctamente."




# -------- VISTAS DE AUTENTICACIÓN Y PERFILES --------
@add_group_name_to_context
class IndexView(TemplateView):
    """Vista de la página principal"""
    template_name = 'index.html'


@add_group_name_to_context
class AddUserView(UserPassesTestMixin, LoginRequiredMixin, CreateView):
    """Vista para agregar nuevos usuarios (solo ADR)"""
    model = User
    form_class = RegisterUserForm
    template_name = 'profiles/add_user.html'
    success_url = reverse_lazy('profile_list')

    def test_func(self):
        """Verifica que el usuario sea ADR"""
        first_group = self.request.user.groups.first()
        return bool(first_group and first_group.name == 'ADR')

    def handle_no_permission(self):
        """Redirecciona a error si no tiene permisos"""
        return redirect('error')

    def get_context_data(self, **kwargs):
        """Agrega grupos al contexto"""
        context = super().get_context_data(**kwargs)
        context['singular_groups'] = Group.objects.values_list('name', 'id')
        return context

    def form_valid(self, form):
        """Crea el usuario con una contraseña aleatoria inservible y le envía el correo de activación"""
        try:
            group_id = self.request.POST.get('group')
            if not group_id:
                messages.error(self.request, 'Debe seleccionar un grupo para el usuario.')
                return self.form_invalid(form)

            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                messages.error(self.request, 'El grupo seleccionado no existe.')
                return self.form_invalid(form)

            with transaction.atomic():
                # 1) Crear usuario
                user = form.save(commit=False)
                user.first_name = form.cleaned_data.get('first_name', '')
                user.last_name  = form.cleaned_data.get('last_name', '')
                
                # Generamos una contraseña aleatoria larga e inútil para el admin.
                # El usuario nunca la usará porque entrará directo por el token del correo.
                user.set_password(get_random_string(32))

                if group.name in ['ADR', 'Operadores ADR']:
                    user.is_staff = True

                user.save()

                # 2) Asignar grupo
                user.groups.clear()
                user.groups.add(group)

                # 3) Crear/actualizar Profile (Aquí ya no necesitas obligatoriamente 'create_by_adr' 
                # para forzar el cambio, ya que el flujo de reset lo hace por diseño)
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.create_by_adr = False # O lo que dicte tu lógica de auditoría
                profile.save()

                enviar_correo_activacion_nuevo_usuario(self.request, user)

            messages.success(self.request, 'Usuario creado exitosamente. Se ha enviado un correo para que establezca su contraseña.')
            return redirect(self.success_url)

        except Exception as e:
            messages.error(self.request, f'Error al crear el usuario: {str(e)}')
            return self.form_invalid(form)

# -------- VISTAS DE PERFILES --------

@add_group_name_to_context
class ProfileListView(LoginRequiredMixin, ListView):
    """Vista para listar los perfiles de usuarios"""
    model = Profile
    template_name = 'profiles/profile_list.html'
    context_object_name = 'profiles'
    paginate_by = 25

    def get_queryset(self):
        """
        Obtiene y configura el queryset de perfiles
        Añade el nombre del grupo y ordena por grupo y nombre de usuario
        """
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            group_name=F('user__groups__name')
        ).order_by('-group_name', 'user__username')
        return queryset

    def get_context_data(self, **kwargs):
        """
        Añade datos adicionales al contexto de la plantilla
        - Información del grupo del usuario actual
        - Lista de perfiles con sus grupos en formato singular
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        group_id, group_name, group_name_singular, color = get_group_and_color(user)
        context['group_name'] = group_name
        context['group_name_singular'] = group_name_singular
        context['color'] = color
        
        profiles_with_singular_groups = []
        for profile in context['profiles']:
            groups = [group.name for group in profile.user.groups.all()]

            profiles_with_singular_groups.append({
                'profile': profile,
                'singular_groups': groups
            })

        context['profiles_with_singular_groups'] = profiles_with_singular_groups
        return context

@add_group_name_to_context
class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    template_name = 'profiles/profile_edit.html'
    context_object_name = 'user_profile'
    form_class = ProfileForm  # Mantén ProfileForm para el perfil

    def get_object(self):
        """Obtiene el perfil a editar usando el pk del perfil"""
        return get_object_or_404(Profile, user__pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        """
        Prepara el contexto para la edición del perfil
        - Incluye formularios de usuario y perfil
        - Añade información de grupos
        """
        context = super().get_context_data(**kwargs)
        profile = self.get_object()
        user = profile.user
        context['user_profile'] = user
        context['profile_form'] = ProfileForm(instance=profile)
        context['user_form'] = UserForm(instance=user)
        context['singular_groups'] = Group.objects.values_list('name', 'id')
        context['group_id_user'] = user.groups.values_list('id', flat=True).first()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        profile = self.object
        user = profile.user

        # --- NUEVO: eliminar solo la foto de perfil (sin tocar otros datos) ---
        if 'delete_image' in request.POST:
            profile.clear_image()
            messages.success(request, 'La foto de perfil fue eliminada y se restauró la imagen por defecto.')
            return redirect(request.path)

        # --- Flujo normal de actualización ---
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

        # Obtener las nuevas contraseñas
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")

        if user_form.is_valid() and profile_form.is_valid():
            # Guardar usuario y perfil
            user_form.save()
            profile_form.save()

            # Asignar grupo
            group_id = request.POST.get('group')
            grupo_asignado = "No asignado"
            if group_id:
                new_group = Group.objects.get(id=group_id)
                user.groups.clear()
                user.groups.add(new_group)
                grupo_asignado = new_group.name

            # Cambio de contraseña (opcional)
            password_cambiada = False
            if new_password1 and new_password1 == new_password2:
                user.set_password(new_password1)
                user.save()
                password_cambiada = True
                messages.success(request, 'Contraseña actualizada exitosamente')
            elif new_password1 or new_password2:
                messages.error(request, 'Las contraseñas no coinciden. Por favor, intente nuevamente.')

            # Notificación por correo
            try:
                from adr.email_template import notificacion_usuario

                ejecutor = request.user.get_full_name() or request.user.username
                datos = [
                    ('Nombre de Usuario', user.username),
                    ('Nombre Completo', f'{user.first_name} {user.last_name}'.strip() or '-'),
                    ('Grupo Asignado', grupo_asignado),
                    ('Contraseña', 'Cambiada' if password_cambiada else 'No Cambiada'),
                ]

                html, plain = notificacion_usuario(
                    accion='Modificación — Perfil de Usuario Actualizado',
                    ejecutor_nombre=ejecutor,
                    datos_usuario=datos,
                )

                enviar_notificacion_asunto(
                    asunto='Actualización de Perfil de Usuario',
                    mensaje=plain,
                    destinatarios=settings.EMAIL_RECIPIENTS,
                    html_content=html,
                )
            except Exception as e:
                print(f"Error al enviar el correo de notificación: {str(e)}")
                messages.error(request, 'Error al enviar el correo de notificación.')

            messages.success(request, 'Usuario editado exitosamente')
            return redirect('profile_list')

        # Errores de validación
        context = self.get_context_data()
        context['user_form'] = user_form
        context['profile_form'] = profile_form
        return render(request, 'profiles/profile_edit.html', context)

    def get_success_url(self):
        """Redirige después de guardar"""
        return reverse_lazy('profile_list')


# --- Helper seguro para enviar correos (no rompe si falla) ---
def _enviar_notificacion(asunto: str, mensaje: str, destinatarios: list[str] | tuple[str, ...] | None):
    """
    Envía un correo simple. Si no hay destinatarios o falla, no levanta excepción.
    Usa DEFAULT_FROM_EMAIL si está definido.
    """
    try:
        if not destinatarios:
            return  # sin destinatarios, no envía
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=from_email,
            recipient_list=list(destinatarios),
            fail_silently=True,  # importantísimo para no romper el flujo
        )
    except Exception:
        # No hacemos nada: el borrado no debe fallar por el correo
        pass


class ProfileDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    success_url = reverse_lazy('profile_list')
    template_name = 'profiles/profile_confirm_delete.html'

    def test_func(self):
        """Solo ADR puede eliminar perfiles"""
        return self.request.user.groups.filter(name='ADR').exists()

    def handle_no_permission(self):
        messages.error(self.request, 'No tiene permisos para esta acción')
        return redirect('error')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.groups.exists():
            group_name = self.request.user.groups.first().name
            context['group_name_singular'] = group_name.replace('es ADR', ' ADR').replace('s ADR', ' ADR')
        return context

    def delete(self, request, *args, **kwargs):
        """Procesa la eliminación de un usuario y envía notificación (sin romper si el correo falla)"""
        try:
            self.object = self.get_object()

            # --- Evitar auto-eliminación (opcional, recomendado) ---
            if self.object == request.user:
                messages.error(request, 'No puedes eliminar tu propia cuenta.')
                return redirect(self.success_url)

            nombre_usuario = self.object.username
            nombre_completo = f"{self.object.first_name} {self.object.last_name}".strip()
            grupo = self.object.groups.first().name if self.object.groups.exists() else "Sin grupo asignado"

            # Eliminar el usuario
            self.object.delete()

            # Preparar y enviar notificación HTML
            try:
                from adr.email_template import notificacion_usuario

                ejecutor = request.user.get_full_name() or request.user.username
                datos = [
                    ('Nombre de Usuario', nombre_usuario),
                    ('Nombre Completo', nombre_completo or '-'),
                    ('Grupo Asignado', grupo),
                ]

                html, plain = notificacion_usuario(
                    accion='Eliminación de Perfil de Usuario',
                    ejecutor_nombre=ejecutor,
                    datos_usuario=datos,
                )

                enviar_notificacion_asunto(
                    asunto='Eliminación de Perfil de Usuario',
                    mensaje=plain,
                    destinatarios=getattr(settings, 'EMAIL_RECIPIENTS', []),
                    html_content=html,
                )
            except Exception:
                pass  # No romper el flujo por fallo de correo

            messages.success(self.request, f'Usuario {nombre_usuario} eliminado exitosamente')
            return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, f'Error al eliminar usuario: {e}')
            return redirect('profile_list')

    def post(self, request, *args, **kwargs):
        # El botón del template hace POST, así que delegamos en delete()
        return self.delete(request, *args, **kwargs)




class PrestamoListView(ListView):
    model = Prestamo
    template_name = 'modulos/lista_prestamos.html'
    context_object_name = 'prestamos'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        # Búsqueda por texto (Nombre o RUT o Sala)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(docente_nombre__icontains=query) |
                Q(docente_rut__icontains=query) |
                Q(sala__icontains=query)
            )
            
        return queryset

class AddPrestamoView(CreateView):
    model = Prestamo
    form_class = PrestamoForm
    template_name = 'modulos/add_prestamo.html'
    success_url = reverse_lazy('prestamos')

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, "Préstamo registrado exitosamente.")
        return super().form_valid(form)

class DevolverPrestamoView(UpdateView):
    model = Prestamo
    fields = ['observaciones'] # Permite actualizar observaciones al devolver si hay daño
    template_name = 'modulos/devolver_prestamo.html'
    success_url = reverse_lazy('prestamos')

    def form_valid(self, form):
        form.instance.estado = 'Devuelto'
        form.instance.fecha_devolucion = timezone.now()
        messages.success(self.request, "El ítem ha sido devuelto exitosamente.")
        return super().form_valid(form)