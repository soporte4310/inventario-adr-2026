from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone # Asegurar que timezone esté importado


class Profile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile', 
        verbose_name='Usuario'
    )
    image = models.ImageField(
        default='default.png', 
        upload_to='users/', 
        verbose_name='Imagen de perfil'
    )
    create_by_adr = models.BooleanField(
        default=True, 
        blank=True, 
        null=True, 
        verbose_name='Creado por ADR'
    )

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
        ordering = ['-id']

    def __str__(self):
        return f"Perfil de {self.user.username}"


    def clear_image(self, save=True):
        """Elimina el archivo (si existe) y deja el campo vacío (None), igual que el admin."""
        if self.image:
            # borra el archivo del storage, pero no guardes aún
            self.image.delete(save=False)
        self.image = None
        if save:
            self.save(update_fields=['image'])

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crea o actualiza el perfil del usuario cuando se crea o actualiza un usuario.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

class LoginAttempt(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='login_attempt')
    failed_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Login attempts for {self.user.username}"

    def is_locked(self):
        if self.lockout_until and self.lockout_until > timezone.now():
            return True
        return False

    def increment_failed_attempts(self):
        self.failed_attempts += 1
        if self.failed_attempts >= 3:  # Límite de intentos
            self.lockout_until = timezone.now() + timezone.timedelta(minutes=5) # Bloqueo por 5 minutos
            # Opcional: resetear failed_attempts a 0 aquí si se prefiere
            # self.failed_attempts = 0
        self.save()

    def reset_attempts(self):
        self.failed_attempts = 0
        self.lockout_until = None
        self.save()