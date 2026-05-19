"""
Vistas para Autenticación y Gestión de Perfil de Usuario
"""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy

from adr.forms import UserUpdateForm, ProfileImageForm


@login_required
def my_profile(request):
    """Vista para gestionar perfil de usuario"""
    user = request.user
    profile = user.profile

    uform = UserUpdateForm(instance=user)
    pform = ProfileImageForm(instance=profile)

    if request.method == "POST":
        # Guardar datos de usuario
        if "save_user" in request.POST:
            uform = UserUpdateForm(request.POST, instance=user)
            if uform.is_valid():
                uform.save()
                messages.success(request, "Datos actualizados correctamente.")
                return redirect("my_profile")
            else:
                messages.error(request, "Revisa los campos del formulario.")

        # Guardar foto de perfil
        elif "save_photo" in request.POST:
            pform = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if pform.is_valid():
                try:
                    pform.save()
                    messages.success(request, "Tu foto de perfil fue actualizada.")
                    return redirect("my_profile")
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al guardar foto de perfil: {str(e)}", exc_info=True)
                    messages.error(request, f"Error al subir la foto: {str(e)}")
            else:
                messages.error(request, "No se pudo actualizar la foto. Revisa el archivo.")

        # Eliminar foto de perfil
        elif "delete_image" in request.POST:
            if profile.image:
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
    """Vista para cambio de contraseña"""
    template_name = "profiles/password_change.html"
    success_url = reverse_lazy("my_profile")
    success_message = "Tu contraseña se cambió correctamente."


class CustomPasswordResetView(PasswordResetView):
    """Vista personalizada para reseteo de contraseña"""
    email_template_name = 'registration/password_reset_email.txt'

    def dispatch(self, request, *args, **kwargs):
        """Redirige a inicio con mensaje de éxito"""
        messages.success(request, "Tu contraseña fue cambiada correctamente.")
        return redirect(reverse_lazy('dashboard_inventario'))
