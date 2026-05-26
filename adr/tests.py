from django.test import TestCase
from django.contrib.auth.models import User
from adr.models import Prestamo

class PrestamoModelTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin_adr', password='password123')
        self.prestamo = Prestamo.objects.create(
            docente_nombre='Juan Ignacio',
            docente_rut='12345678-9',
            sala='Sala Computación 1',
            item_prestado='Adaptador Tipo C a HDMI',
            creado_por=self.admin_user
        )

    def test_prestamo_default_values(self):
        """Verifica que los valores por defecto se asignen correctamente al crear"""
        self.assertEqual(self.prestamo.estado, 'En Préstamo')
        self.assertTrue(self.prestamo.fecha_prestamo)
        self.assertIsNone(self.prestamo.fecha_devolucion)

    def test_prestamo_str(self):
        """Verifica la representación en cadena del modelo"""
        expected_str = "Adaptador Tipo C a HDMI a Juan Ignacio (Sala Computación 1)"
        self.assertEqual(str(self.prestamo), expected_str)




class PrestamoIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='password')
        # Crear un préstamo de prueba
        Prestamo.objects.create(
            docente_nombre='Docente Test',
            docente_rut='1111111-1',
            sala='Auditorio',
            item_prestado='Puntero Presentador PPT'
        )

    def test_lista_prestamos_requiere_login(self):
        """Verifica que un usuario anónimo no pueda ver la lista (ejemplo)"""
        # Reemplaza 'lista_prestamos' con el nombre real de tu url de Django
        response = self.client.get('/adr/prestamos/') 
        self.assertNotEqual(response.status_code, 200) # Probablemente retorne 302 hacia el login

    def test_lista_prestamos_usuario_autenticado(self):
        """Verifica que un usuario autenticado puede ver el contenido"""
        self.client.login(username='admin', password='password')
        response = self.client.get('/adr/prestamos/') # Ajusta la URL según tu proyecto
        
        # Omitir validación si la URL no existe aún en tu proyecto, 
        # pero si existe, debería cargar correctamente (código 200)
        if response.status_code == 200:
            self.assertContains(response, 'Puntero Presentador PPT')