from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import Profile, LoginAttempt

class AccountsModelTests(TestCase):
    def setUp(self):
        # Esta función se ejecuta antes de cada prueba para preparar datos
        self.user = User.objects.create_user(username='funcionario_test', password='password123')

    def test_profile_creation_signal(self):
        """Verifica que al crear un User, automáticamente se crea un Profile"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.user, self.user)
        self.assertEqual(str(self.user.profile), "Perfil de funcionario_test")

    def test_login_attempt_increment_and_lock(self):
        """Verifica que a los 3 intentos el usuario se bloquea por 5 minutos"""
        attempt = LoginAttempt.objects.create(user=self.user)
        self.assertFalse(attempt.is_locked())

        # Simulamos 3 intentos fallidos
        attempt.increment_failed_attempts()
        attempt.increment_failed_attempts()
        attempt.increment_failed_attempts()

        self.assertTrue(attempt.is_locked())
        self.assertEqual(attempt.failed_attempts, 3)
        self.assertIsNotNone(attempt.lockout_until)

    def test_login_attempt_reset(self):
        """Verifica que el reset limpia los intentos y el bloqueo"""
        attempt = LoginAttempt.objects.create(
            user=self.user, 
            failed_attempts=3, 
            lockout_until=timezone.now() + timedelta(minutes=5)
        )
        self.assertTrue(attempt.is_locked())

        attempt.reset_attempts()
        self.assertFalse(attempt.is_locked())
        self.assertEqual(attempt.failed_attempts, 0)
        self.assertIsNone(attempt.lockout_until)