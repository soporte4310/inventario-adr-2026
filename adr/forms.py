"""
forms.py - Archivo de formularios de la aplicación
Contiene todos los formularios necesarios para manejar los diferentes modelos y funcionalidades
"""

from datetime import datetime

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from PIL import Image

from accounts.models import Profile
from .models import (
    AllInOne, AllInOneAdmins, Notebook, MiniPC,
    Proyectores, BodegaADR, Azotea, Monitor, Audio, Tablet,
    EquiposIsla, SwitchDeRed, Televisor,Prestamo,
)
from .utils import make_avatar_square


def _lock_key(username=None, ip=None):
    return f"login_lock:{username or 'unknown'}:{ip or 'unknown'}"
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "w-full h-10 rounded-lg border border-zinc-300 px-3 shadow-sm"
            }),
            "first_name": forms.TextInput(attrs={
                "class": "w-full h-10 rounded-lg border border-zinc-300 px-3 shadow-sm"
            }),
            "last_name": forms.TextInput(attrs={
                "class": "w-full h-10 rounded-lg border border-zinc-300 px-3 shadow-sm"
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full h-10 rounded-lg border border-zinc-300 px-3 shadow-sm"
            }),
        }
    def clean_username(self):
        username = self.cleaned_data.get("username").strip().lower()
        if User.objects.exclude(pk=self.instance.pk).filter(username__iexact=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

class LoginForm(AuthenticationForm):
    def clean(self):
        User = get_user_model()
        uname_field = getattr(User, "USERNAME_FIELD", "username")

        # toma el valor ingresado sin importar el nombre del input
        username = (self.data.get(uname_field) or self.data.get("username") or "").strip().lower()
        ip = self.request.META.get("REMOTE_ADDR") if self.request else None

        lock_until_iso = cache.get(_lock_key(username, ip))
        if lock_until_iso:
            try:
                lock_until = datetime.fromisoformat(lock_until_iso)
            except Exception:
                lock_until = None

            if lock_until and lock_until > timezone.now():
                remaining = int((lock_until - timezone.now()).total_seconds())
                m, s = divmod(remaining, 60)
                raise forms.ValidationError(
                    f"Acceso bloqueado por seguridad. Intenta nuevamente en {m:02d}:{s:02d}."
                )
            else:
                cache.delete(_lock_key(username, ip))

        return super().clean()
# -------- FORMULARIOS DE AUTENTICACIÓN --------
class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["image"]

    def clean_image(self):
        f = self.cleaned_data.get("image")
        if not f:
            return f

        # Tamaño (2 MB de ejemplo)
        if f.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Máximo 2 MB.")

        # Resolución mínima
        try:
            img = Image.open(f)
            w, h = img.size
            if w < 400 or h < 400:
                raise forms.ValidationError("Resolución mínima: 400×400 px.")
            f.seek(0)  # importante: rebobinar
        except Exception:
            raise forms.ValidationError("Archivo de imagen inválido.")

        return f

    def save(self, commit=True):
        profile = super().save(commit=False)
        f = self.cleaned_data.get("image")
        if f:
            try:
                # Procesa a cuadrado de 512 (calidad alta) y guarda como WEBP
                processed = make_avatar_square(f, size=512, fmt="WEBP", quality=86)
                profile.image.save(processed.name, processed, save=False)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error procesando imagen: {str(e)}", exc_info=True)
                # Re-lanzar el error para que sea manejado en la vista
                raise forms.ValidationError(
                    f"Error al procesar la imagen: {str(e)}. "
                    "Verifica tu conexión y las credenciales de Cloudinary."
                )

        if commit:
            try:
                profile.save(update_fields=["image"])
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error guardando en Cloudinary: {str(e)}", exc_info=True)
                # Proporcionar mensaje más específico según el error
                error_msg = str(e)
                if "quota" in error_msg.lower():
                    raise forms.ValidationError("Límite de almacenamiento de Cloudinary alcanzado.")
                elif "unauthorized" in error_msg.lower() or "credentials" in error_msg.lower():
                    raise forms.ValidationError("Error de autenticación con Cloudinary. Contacta al administrador.")
                elif "timeout" in error_msg.lower():
                    raise forms.ValidationError("Tiempo de espera agotado. Intenta con una imagen más pequeña.")
                else:
                    raise forms.ValidationError(f"Error al subir a Cloudinary: {error_msg}")
        return profile
class LoginForm(AuthenticationForm):
    """Formulario de inicio de sesión"""
    pass

class RegisterUserForm(forms.ModelForm):
    """Formulario para registro de nuevos usuarios"""
    # Campos adicionales requeridos
    first_name = forms.CharField(label='Nombres', required=True)
    last_name = forms.CharField(label='Apellidos', required=True)
    password1 = forms.CharField(
        label='Contraseña', 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        required=True
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña', 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar Contraseña'}),
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Nombre de Usuario'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Correo Electrónico'}),
        }

    def clean_email(self):
        """Validación personalizada para email único"""
        email_field = self.cleaned_data.get('email')
        if User.objects.filter(email=email_field).exists():
            raise forms.ValidationError('Este email ya existe en los registros')
        return email_field

    def clean(self):
        """Validación personalizada para verificar que las contraseñas coincidan"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Las contraseñas no coinciden")

        # Validación de fortaleza de contraseña (opcional)
        if password1:
            if len(password1) < 8:
                self.add_error("password1", "La contraseña debe tener al menos 8 caracteres")
            if not any(char.isdigit() for char in password1):
                self.add_error("password1", "La contraseña debe contener al menos un número")
            if not any(char.isalpha() for char in password1):
                self.add_error("password1", "La contraseña debe contener al menos una letra")

        return cleaned_data

class UserForm(forms.ModelForm):
    """Formulario para actualización de datos básicos del usuario"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name','email']

class ProfileForm(forms.ModelForm):
    """Formulario para el perfil de usuario"""
    class Meta:
        model = Profile
        fields = ['image']




class PrestamoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = ['docente_nombre', 'docente_rut', 'sala', 'item_prestado', 'observaciones']
        widgets = {
            'docente_nombre': forms.TextInput(attrs={
                'class': 'w-full h-10 px-3 rounded-md border border-gray-300 shadow-sm focus:border-red-500 focus:ring-red-500', 
                'placeholder': 'Ej. Juan Pérez'
            }),
            'docente_rut': forms.TextInput(attrs={
                'class': 'w-full h-10 px-3 rounded-md border border-gray-300 shadow-sm focus:border-red-500 focus:ring-red-500', 
                'placeholder': 'Ej. 12345678-9'
            }),
            'sala': forms.TextInput(attrs={
                'class': 'w-full h-10 px-3 rounded-md border border-gray-300 shadow-sm focus:border-red-500 focus:ring-red-500', 
                'placeholder': 'Ej. Sala 205'
            }),
            'item_prestado': forms.Select(attrs={
                'class': 'w-full h-10 px-3 rounded-md border border-gray-300 shadow-sm focus:border-red-500 focus:ring-red-500 bg-white'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'w-full p-3 rounded-md border border-gray-300 shadow-sm focus:border-red-500 focus:ring-red-500', 
                'rows': 3, 
                'placeholder': 'Opcional: Detalles del equipo (Ej. Mouse HP n/s 1234)'
            }),
        }

    def clean_docente_rut(self):
        # Limpieza básica para estandarizar el RUT
        rut = self.cleaned_data.get('docente_rut')
        if rut:
            rut = rut.replace('.', '').strip().upper()
        return rut