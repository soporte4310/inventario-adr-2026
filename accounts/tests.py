from django.test import TestCase
from django.contrib.auth.models import Group, User
from django.utils import timezone
from datetime import timedelta
from accounts.models import Profile, LoginAttempt, RegistroAcceso

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

class RegistroAccesoTests(TestCase):
    """Verifica que cada intento de login queda auditado en RegistroAcceso."""

    def setUp(self):
        self.user = User.objects.create_user(username='accesos_test', password='clave-segura-123')
        self.grupo_adr, _ = Group.objects.get_or_create(name='ADR')

    def test_login_exitoso_queda_registrado(self):
        self.client.post('/accounts/login/', {'username': 'accesos_test', 'password': 'clave-segura-123'})
        registro = RegistroAcceso.objects.latest('fecha')
        self.assertEqual(registro.resultado, RegistroAcceso.Resultado.EXITOSO)
        self.assertEqual(registro.usuario, self.user)
        self.assertEqual(registro.portal, RegistroAcceso.Portal.INVENTARIO)

    def test_contrasena_incorrecta_queda_registrada(self):
        self.client.post('/accounts/login/', {'username': 'accesos_test', 'password': 'clave-mala'})
        registro = RegistroAcceso.objects.latest('fecha')
        self.assertEqual(registro.resultado, RegistroAcceso.Resultado.CONTRASENA_INCORRECTA)
        self.assertEqual(registro.usuario, self.user)

    def test_usuario_inexistente_queda_registrado_sin_fk(self):
        self.client.post('/accounts/login/', {'username': 'no_existe_nadie', 'password': 'x'})
        registro = RegistroAcceso.objects.latest('fecha')
        self.assertEqual(registro.resultado, RegistroAcceso.Resultado.USUARIO_INEXISTENTE)
        self.assertIsNone(registro.usuario)
        self.assertEqual(registro.username_ingresado, 'no_existe_nadie')

    def test_cuenta_desactivada_queda_registrada(self):
        self.user.is_active = False
        self.user.save()
        self.client.post('/accounts/login/', {'username': 'accesos_test', 'password': 'clave-segura-123'})
        registro = RegistroAcceso.objects.latest('fecha')
        self.assertEqual(registro.resultado, RegistroAcceso.Resultado.CUENTA_DESACTIVADA)

    def test_pagina_de_auditoria_solo_para_adr(self):
        self.client.login(username='accesos_test', password='clave-segura-123')
        resp = self.client.get('/accounts/accesos/')
        self.assertEqual(resp.status_code, 403)

        self.user.groups.add(self.grupo_adr)
        resp = self.client.get('/accounts/accesos/')
        self.assertEqual(resp.status_code, 200)
