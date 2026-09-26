import io
import tempfile

from PIL import Image

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from inventario.models import Activo, AuditoriaActivo, Catalogo, Categoria, Edificio, Estado, Marca, Piso, Ubicacion

from .models import CicloRevision, EquipoMantenible, Impresora, RegistroAuditoria, RevisionEquipo


def _imagen_valida():
    """Genera una imagen JPEG mínima en memoria para simular una evidencia subida."""
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile('evidencia.jpg', buffer.read(), content_type='image/jpeg')


class MantencionTestCase(TestCase):
    """
    Fixtures compartidos por todos los tests del módulo: un edificio con dos
    salas y un proyector ya inventariado, más un usuario por cada grupo
    relevante (ADR, Alumno en Práctica, Visitante).
    """

    def setUp(self):
        self.edificio = Edificio.objects.create(nombre="Edificio A")
        self.piso = Piso.objects.create(nombre="Piso 1", edificio=self.edificio)
        self.sala_101 = Ubicacion.objects.create(nombre="Sala 101A", piso=self.piso)
        self.sala_102 = Ubicacion.objects.create(nombre="Sala 102A", piso=self.piso)

        categoria = Categoria.objects.create(nombre="Proyector")
        marca = Marca.objects.create(nombre="Epson")
        catalogo = Catalogo.objects.create(categoria=categoria, marca=marca, modelo="X100")
        estado_operativo = Estado.objects.create(nombre="Operativo")

        self.activo = Activo.objects.create(
            catalogo=catalogo, numero_serie="SN-001", estado=estado_operativo,
            ubicacion=self.sala_101,
        )
        self.equipo = EquipoMantenible.objects.create(activo=self.activo, tipo=EquipoMantenible.Tipo.PROYECTOR)

        # Mismos nombres de grupo que existen en la base real (ver
        # mantencion/utils.py::GRUPOS_REVISION para el porqué del plural).
        Group.objects.get_or_create(name='ADR')
        Group.objects.get_or_create(name='Alumnos en Práctica')
        Group.objects.get_or_create(name='Usuario')

        self.user_adr = User.objects.create_user(username='adr1', password='clave-segura-123')
        self.user_adr.groups.add(Group.objects.get(name='ADR'))

        self.user_practicante = User.objects.create_user(username='practicante1', password='clave-segura-123')
        self.user_practicante.groups.add(Group.objects.get(name='Alumnos en Práctica'))

        self.user_visitante = User.objects.create_user(username='visitante1', password='clave-segura-123')
        self.user_visitante.groups.add(Group.objects.get(name='Usuario'))

        # El signal de accounts crea un Profile con create_by_adr=True por
        # defecto (fuerza cambio de clave en el primer login). Para los
        # tests de flujo normal, simulamos usuarios que ya hicieron ese
        # cambio alguna vez.
        for user in (self.user_adr, self.user_practicante, self.user_visitante):
            user.profile.create_by_adr = False
            user.profile.save()


class RosterModelTests(MantencionTestCase):
    def test_equipo_mantenible_se_crea_correctamente(self):
        """Un Activo ya inventariado queda enlazado (no duplicado) al roster de mantención."""
        self.assertEqual(self.equipo.activo, self.activo)
        self.assertTrue(self.equipo.activo_en_revision)


class ComandoGenerarCicloTests(MantencionTestCase):
    def test_comando_crea_una_fila_pendiente_por_equipo_activo(self):
        call_command('generar_ciclo_revision', 'PROY')

        ciclo = CicloRevision.objects.get(tipo='PROY')
        revision = RevisionEquipo.objects.get(ciclo=ciclo, equipo=self.equipo)

        self.assertEqual(ciclo.fecha_inicio, timezone.localdate())
        self.assertEqual(revision.estado, RevisionEquipo.Estado.PENDIENTE)
        self.assertEqual(revision.ubicacion_en_revision, self.sala_101)

    def test_cada_llamada_abre_un_ciclo_nuevo(self):
        """A diferencia de la versión mensual anterior, esto ya no es idempotente: cada llamada = una ronda nueva."""
        call_command('generar_ciclo_revision', 'PROY')
        call_command('generar_ciclo_revision', 'PROY')

        self.assertEqual(CicloRevision.objects.filter(tipo='PROY').count(), 2)
        self.assertEqual(RevisionEquipo.objects.count(), 2)

    def test_ciclos_de_proyectores_e_impresoras_son_independientes(self):
        call_command('generar_ciclo_revision', 'PROY')
        call_command('generar_ciclo_revision', 'IMPR')

        self.assertEqual(CicloRevision.objects.filter(tipo='PROY').count(), 1)
        self.assertEqual(CicloRevision.objects.filter(tipo='IMPR').count(), 1)
        # El ciclo de impresoras no genera filas: self.equipo es un proyector.
        self.assertEqual(RevisionEquipo.objects.filter(ciclo__tipo='IMPR').count(), 0)

    def test_comando_ignora_equipos_pausados(self):
        self.equipo.activo_en_revision = False
        self.equipo.save(update_fields=['activo_en_revision'])

        call_command('generar_ciclo_revision', 'PROY')

        self.assertEqual(RevisionEquipo.objects.count(), 0)

    def test_comando_ignora_activos_eliminados(self):
        self.activo.is_deleted = True
        self.activo.save()

        call_command('generar_ciclo_revision', 'PROY')

        self.assertEqual(RevisionEquipo.objects.count(), 0)


class PermisosVistasTests(MantencionTestCase):
    def test_anonimo_es_redirigido_al_login_propio_de_mantencion(self):
        """Mantención tiene su propia puerta de entrada, no la de accounts/inventario."""
        response = self.client.get(reverse('mantencion_home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('mantencion_login'), response.url)

    def test_visitante_no_puede_ver_revision_mensual(self):
        self.client.login(username='visitante1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_revision_proyectores'))
        self.assertEqual(response.status_code, 403)

    def test_practicante_si_puede_ver_revision_mensual(self):
        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_revision_proyectores'))
        self.assertEqual(response.status_code, 200)

    def test_practicante_no_puede_administrar_roster(self):
        """Sólo ADR administra el roster de equipos y la estructura de edificios."""
        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_roster'))
        self.assertEqual(response.status_code, 403)

    def test_adr_si_puede_administrar_roster(self):
        self.client.login(username='adr1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_roster'))
        self.assertEqual(response.status_code, 200)

    def test_home_y_listas_renderizan_ok_para_practicante(self):
        self.client.login(username='practicante1', password='clave-segura-123')
        for url_name in ('mantencion_home', 'mantencion_lista_proyectores', 'mantencion_lista_impresoras'):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200, f"{url_name} no respondió 200")


class EnroqueAuditoriaTests(MantencionTestCase):
    def test_enroque_mueve_activo_y_queda_auditado(self):
        """
        Mover un equipo de sala desde mantención debe actualizar el Activo
        real de inventario y quedar registrado en su auditoría automática.
        Sólo ADR puede hacerlo (requiere planificación previa).
        """
        self.client.login(username='adr1', password='clave-segura-123')
        url = reverse('mantencion_enroque', args=[self.equipo.pk])
        response = self.client.post(url, {'ubicacion': self.sala_102.pk})

        self.activo.refresh_from_db()
        self.assertEqual(self.activo.ubicacion, self.sala_102)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            AuditoriaActivo.objects.filter(object_id=self.activo.pk, campo__icontains='Ubicaci').exists()
        )

    def test_practicante_no_puede_hacer_enroque(self):
        """El enroque requiere planificación previa: sólo ADR, no cualquier revisor."""
        self.client.login(username='practicante1', password='clave-segura-123')
        url = reverse('mantencion_enroque', args=[self.equipo.pk])
        response = self.client.post(url, {'ubicacion': self.sala_102.pk})

        self.assertEqual(response.status_code, 403)
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.ubicacion, self.sala_101)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RevisionMensualFlowTests(MantencionTestCase):
    def test_marcar_ok_actualiza_estado_y_revisor(self):
        call_command('generar_ciclo_revision', 'PROY')
        revision = RevisionEquipo.objects.get(equipo=self.equipo)

        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.post(reverse('mantencion_marcar_ok', args=[revision.pk]))

        revision.refresh_from_db()
        self.assertEqual(revision.estado, RevisionEquipo.Estado.OK)
        self.assertEqual(revision.revisado_por, self.user_practicante)
        self.assertEqual(response.status_code, 302)
        # El redirect deja al navegador en la misma tarjeta (no arriba de la página).
        self.assertTrue(response.url.endswith(f"#revision-{revision.pk}"))

    def test_marcar_ok_deja_registro_en_la_bitacora_de_auditoria(self):
        call_command('generar_ciclo_revision', 'PROY')
        revision = RevisionEquipo.objects.get(equipo=self.equipo)

        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_marcar_ok', args=[revision.pk]))

        registro = RegistroAuditoria.objects.latest('id')
        self.assertEqual(registro.accion, RegistroAuditoria.Accion.REVISION_OK)
        self.assertEqual(registro.usuario, self.user_practicante)
        self.assertIn(self.activo.numero_serie, registro.equipo_descripcion)

    def test_registrar_novedad_guarda_evidencia_como_jpeg(self):
        call_command('generar_ciclo_revision', 'PROY')
        revision = RevisionEquipo.objects.get(equipo=self.equipo)

        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_registrar_novedad', args=[revision.pk]), {
            'comentario': 'No enciende',
            'sigue_operativo': 'False',
            'archivo': _imagen_valida(),
        })

        revision.refresh_from_db()
        self.assertEqual(revision.estado, RevisionEquipo.Estado.NOVEDAD)
        self.assertFalse(revision.sigue_operativo)
        self.assertEqual(revision.evidencias.count(), 1)

        evidencia = revision.evidencias.first()
        self.assertEqual(evidencia.tipo_archivo, 'FOTO')

    def test_registrar_novedad_operativo_true_se_guarda_correctamente(self):
        """Una observación superficial (ej: rayadura estética) no implica que el equipo dejó de funcionar."""
        call_command('generar_ciclo_revision', 'PROY')
        revision = RevisionEquipo.objects.get(equipo=self.equipo)

        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_registrar_novedad', args=[revision.pk]), {
            'comentario': 'Carcasa rayada, funciona con normalidad',
            'sigue_operativo': 'True',
            'archivo': _imagen_valida(),
        })

        revision.refresh_from_db()
        self.assertEqual(revision.estado, RevisionEquipo.Estado.NOVEDAD)
        self.assertTrue(revision.sigue_operativo)

    def test_registrar_novedad_sin_responder_operatividad_no_guarda(self):
        """El campo es obligatorio: no se debe poder registrar una novedad sin contestar la pregunta."""
        call_command('generar_ciclo_revision', 'PROY')
        revision = RevisionEquipo.objects.get(equipo=self.equipo)

        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_registrar_novedad', args=[revision.pk]), {
            'comentario': 'No enciende',
            'archivo': _imagen_valida(),
        })

        revision.refresh_from_db()
        self.assertEqual(revision.estado, RevisionEquipo.Estado.PENDIENTE)
        self.assertEqual(revision.evidencias.count(), 0)


class HistorialDeCiclosTests(MantencionTestCase):
    """
    El ciclo más reciente de un tipo es el único editable; todo ciclo
    anterior queda como historial de sólo lectura (no se puede marcar OK
    ni registrar novedades sobre una revisión de un ciclo cerrado).
    """

    def test_nuevo_ciclo_cierra_el_anterior(self):
        self.client.login(username='practicante1', password='clave-segura-123')

        r1 = self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))
        ciclo_viejo = CicloRevision.objects.filter(tipo='PROY').latest('id')
        self.assertEqual(r1.status_code, 302)

        r2 = self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))
        ciclo_nuevo = CicloRevision.objects.filter(tipo='PROY').exclude(pk=ciclo_viejo.pk).latest('id')
        self.assertEqual(r2.status_code, 302)

        # El más reciente por fecha_inicio/fecha_generado es "ciclo_nuevo".
        self.assertEqual(CicloRevision.objects.filter(tipo='PROY').first().pk, ciclo_nuevo.pk)

    def test_no_se_puede_marcar_ok_en_un_ciclo_historico(self):
        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))
        revision_vieja = RevisionEquipo.objects.get(equipo=self.equipo)

        # Se abre un segundo ciclo: el primero queda cerrado.
        self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))

        response = self.client.post(reverse('mantencion_marcar_ok', args=[revision_vieja.pk]))
        revision_vieja.refresh_from_db()

        self.assertEqual(revision_vieja.estado, RevisionEquipo.Estado.PENDIENTE)
        self.assertEqual(response.status_code, 302)

    def test_revision_mensual_muestra_ciclo_seleccionado_como_no_editable(self):
        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))
        ciclo_viejo = CicloRevision.objects.filter(tipo='PROY').first()
        self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))

        response = self.client.get(reverse('mantencion_revision_proyectores'), {'ciclo': ciclo_viejo.pk})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['es_editable'])
        self.assertEqual(response.context['ciclo'].pk, ciclo_viejo.pk)

    def test_revision_mensual_por_defecto_muestra_el_mas_reciente_editable(self):
        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))
        self.client.post(reverse('mantencion_nuevo_ciclo_proyectores'))

        response = self.client.get(reverse('mantencion_revision_proyectores'))

        self.assertTrue(response.context['es_editable'])


class LoginPropioTests(MantencionTestCase):
    def test_pagina_de_login_renderiza_ok(self):
        response = self.client.get(reverse('mantencion_login'))
        self.assertEqual(response.status_code, 200)

    def test_login_correcto_redirige_a_mantencion_home_por_defecto(self):
        response = self.client.post(reverse('mantencion_login'), {
            'username': 'practicante1', 'password': 'clave-segura-123',
        })
        self.assertRedirects(response, reverse('mantencion_home'))

    def test_login_respeta_next_hacia_una_pagina_interna(self):
        destino = reverse('mantencion_lista_proyectores')
        response = self.client.post(f"{reverse('mantencion_login')}?next={destino}", {
            'username': 'practicante1', 'password': 'clave-segura-123',
        })
        self.assertRedirects(response, destino)

    def test_logout_vuelve_al_login_de_mantencion(self):
        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.post(reverse('mantencion_logout'))
        self.assertRedirects(response, reverse('mantencion_login'))


class FormularioAgregarProyectorTests(MantencionTestCase):
    def test_solo_ofrece_activos_de_categoria_proyector_y_no_inscritos(self):
        """El combo de 'Agregar proyector' no debe mezclarse con impresoras (que ya ni son Activo)."""
        categoria_proyector = Categoria.objects.get(nombre__iexact="Proyector")
        categoria_otra = Categoria.objects.create(nombre="Monitor")
        marca, _ = Marca.objects.get_or_create(nombre="Epson")
        estado_operativo = Estado.objects.get(nombre__iexact="Operativo")

        # self.activo ya está inscrito en el roster (ver setUp), así que
        # usamos OTRO proyector todavía sin inscribir para probar el filtro.
        catalogo_proy = Catalogo.objects.create(categoria=categoria_proyector, marca=marca, modelo="X200")
        proyector_nuevo = Activo.objects.create(catalogo=catalogo_proy, numero_serie="SN-PROY-2", estado=estado_operativo)

        catalogo_otro = Catalogo.objects.create(categoria=categoria_otra, marca=marca, modelo="M100")
        otro_activo = Activo.objects.create(catalogo=catalogo_otro, numero_serie="SN-OTRO", estado=estado_operativo)

        from .forms import AgregarProyectorForm

        form = AgregarProyectorForm()
        activos_disponibles = list(form.fields['activo'].queryset)

        self.assertIn(proyector_nuevo, activos_disponibles)
        self.assertNotIn(otro_activo, activos_disponibles)
        self.assertNotIn(self.activo, activos_disponibles)  # ya inscrito en setUp

    def test_no_permite_agregar_un_activo_que_no_este_operativo(self):
        """Un equipo dañado/de baja no debería poder inscribirse sin corroborar con inventario."""
        categoria_proyector = Categoria.objects.get(nombre__iexact="Proyector")
        marca, _ = Marca.objects.get_or_create(nombre="Epson")
        estado_danado = Estado.objects.create(nombre="Dañado")
        catalogo = Catalogo.objects.create(categoria=categoria_proyector, marca=marca, modelo="X300")
        proyector_danado = Activo.objects.create(catalogo=catalogo, numero_serie="SN-DAN-1", estado=estado_danado)

        from .forms import AgregarProyectorForm

        form = AgregarProyectorForm(data={'activo': proyector_danado.pk})
        self.assertFalse(form.is_valid())
        self.assertIn('activo', form.errors)


class UbicacionAgrupadaTests(MantencionTestCase):
    def test_choices_de_ubicacion_quedan_agrupadas_por_edificio_y_piso(self):
        from .forms import EnroqueActivoForm

        form = EnroqueActivoForm(instance=self.activo)
        etiquetas_grupo = [
            etiqueta for etiqueta, opciones in form.fields['ubicacion'].choices
            if isinstance(opciones, list)
        ]
        self.assertIn(f"{self.edificio.nombre} · {self.piso.nombre}", etiquetas_grupo)

    def test_bodegas_quedan_primero_y_en_grupo_aparte(self):
        """Al devolver un equipo, la bodega debe encontrarse sin buscar entre los edificios."""
        bodega = Ubicacion.objects.create(nombre="Bodega ADR", piso=self.piso)

        from .forms import EnroqueActivoForm

        form = EnroqueActivoForm(instance=self.activo)
        choices = list(form.fields['ubicacion'].choices)

        etiquetas_grupo = [etiqueta for etiqueta, opciones in choices if isinstance(opciones, list)]
        self.assertEqual(etiquetas_grupo[0], 'Disponible / Bodega')

        opciones_bodega = dict(choices)['Disponible / Bodega']
        self.assertIn((bodega.pk, bodega.nombre), opciones_bodega)

        # La bodega no debe aparecer duplicada en el grupo de su edificio/piso.
        etiqueta_edificio = f"{self.edificio.nombre} · {self.piso.nombre}"
        opciones_edificio = dict(choices)[etiqueta_edificio]
        self.assertNotIn((bodega.pk, bodega.nombre), opciones_edificio)


class ImpresoraTestCase(MantencionTestCase):
    """Fixture extra: una Impresora real (no-Activo) inscrita en el roster."""

    def setUp(self):
        super().setUp()
        self.impresora = Impresora.objects.create(
            marca="HP", modelo="E42540", numero_serie="CNBRRBT5H4",
            ip="172.16.5.157", codigo_proveedor="7090727", ubicacion=self.sala_101,
        )
        self.equipo_impresora = EquipoMantenible.objects.create(
            tipo=EquipoMantenible.Tipo.IMPRESORA, impresora=self.impresora
        )


class EquipoMantenibleGenericoTests(ImpresoraTestCase):
    """
    equipo.equipo_real / marca_modelo / numero_serie / ubicacion deben
    funcionar igual para un proyector (Activo) que para una impresora
    (Impresora), sin que las plantillas tengan que distinguir el tipo.
    """

    def test_propiedades_genericas_para_proyector(self):
        self.assertEqual(self.equipo.equipo_real, self.activo)
        self.assertEqual(self.equipo.numero_serie, self.activo.numero_serie)
        self.assertEqual(self.equipo.ubicacion, self.sala_101)

    def test_propiedades_genericas_para_impresora(self):
        self.assertEqual(self.equipo_impresora.equipo_real, self.impresora)
        self.assertEqual(self.equipo_impresora.numero_serie, "CNBRRBT5H4")
        self.assertEqual(self.equipo_impresora.ubicacion, self.sala_101)
        self.assertIn("HP", self.equipo_impresora.marca_modelo)

    def test_no_puede_tener_activo_e_impresora_a_la_vez(self):
        from django.core.exceptions import ValidationError

        equipo_invalido = EquipoMantenible(
            tipo=EquipoMantenible.Tipo.PROYECTOR, activo=self.activo, impresora=self.impresora
        )
        with self.assertRaises(ValidationError):
            equipo_invalido.full_clean()


class ImpresoraAltaBajaTests(ImpresoraTestCase):
    def test_adr_puede_agregar_una_impresora_nueva(self):
        self.client.login(username='adr1', password='clave-segura-123')
        response = self.client.post(reverse('mantencion_impresora_agregar'), {
            'marca': 'HP', 'modelo': 'E731', 'numero_serie': 'NUEVA-001',
            'tipo_impresion': 'Blanco y Negro', 'ubicacion': self.sala_102.pk,
        })

        self.assertEqual(response.status_code, 302)
        impresora_nueva = Impresora.objects.get(numero_serie='NUEVA-001')
        self.assertEqual(impresora_nueva.estado, Impresora.EstadoImpresora.OPERATIVA)
        self.assertTrue(EquipoMantenible.objects.filter(impresora=impresora_nueva).exists())

    def test_practicante_no_puede_agregar_impresoras(self):
        """Sólo ADR agrega/elimina impresoras (son ajenas a inventario, hay que tener cuidado)."""
        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.post(reverse('mantencion_impresora_agregar'), {
            'marca': 'HP', 'modelo': 'E731', 'numero_serie': 'NUEVA-002', 'ubicacion': '',
        })
        self.assertEqual(response.status_code, 403)

class CicloImpresorasTests(ImpresoraTestCase):
    def test_generar_ciclo_revision_impr_crea_fila_para_impresora_real(self):
        call_command('generar_ciclo_revision', 'IMPR')

        revision = RevisionEquipo.objects.get(equipo=self.equipo_impresora)
        self.assertEqual(revision.estado, RevisionEquipo.Estado.PENDIENTE)
        self.assertEqual(revision.ubicacion_en_revision, self.sala_101)

    def test_generar_ciclo_ignora_impresoras_de_baja(self):
        self.impresora.estado = Impresora.EstadoImpresora.DE_BAJA
        self.impresora.save()

        call_command('generar_ciclo_revision', 'IMPR')

        self.assertFalse(RevisionEquipo.objects.filter(equipo=self.equipo_impresora).exists())

    def test_reporte_excel_bloqueado_si_quedan_pendientes(self):
        """El reporte no refleja la realidad si todavía faltan equipos por revisar."""
        call_command('generar_ciclo_revision', 'IMPR')
        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_reporte_excel_impresoras'))

        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(
            response.get('Content-Type'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_reporte_email_bloqueado_si_quedan_pendientes(self):
        call_command('generar_ciclo_revision', 'IMPR')
        self.client.login(username='practicante1', password='clave-segura-123')
        ciclo = CicloRevision.objects.filter(tipo='IMPR').first()
        response = self.client.post(reverse('mantencion_reporte_email_impresoras'), {'ciclo': ciclo.pk})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_reporte_excel_impresoras_funciona_con_el_ciclo_completo(self):
        call_command('generar_ciclo_revision', 'IMPR')
        revision = RevisionEquipo.objects.get(equipo=self.equipo_impresora)
        self.client.login(username='practicante1', password='clave-segura-123')
        self.client.post(reverse('mantencion_marcar_ok', args=[revision.pk]))

        response = self.client.get(reverse('mantencion_reporte_excel_impresoras'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_enroque_de_impresora_mueve_su_ubicacion(self):
        self.client.login(username='adr1', password='clave-segura-123')
        url = reverse('mantencion_enroque', args=[self.equipo_impresora.pk])
        response = self.client.post(url, {'ubicacion': self.sala_102.pk})

        self.impresora.refresh_from_db()
        self.assertEqual(self.impresora.ubicacion, self.sala_102)
        self.assertEqual(response.status_code, 302)


class AuditoriaMantencionTests(MantencionTestCase):
    def test_practicante_no_puede_ver_la_auditoria(self):
        """Auditoría es sólo lectura para ADR, ni siquiera los revisores de terreno la ven."""
        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_auditoria'))
        self.assertEqual(response.status_code, 403)

    def test_adr_si_puede_ver_la_auditoria(self):
        self.client.login(username='adr1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_auditoria'))
        self.assertEqual(response.status_code, 200)

    def test_enroque_deja_registro_con_ubicacion_anterior_y_nueva(self):
        self.client.login(username='adr1', password='clave-segura-123')
        self.client.post(reverse('mantencion_enroque', args=[self.equipo.pk]), {'ubicacion': self.sala_102.pk})

        registro = RegistroAuditoria.objects.latest('id')
        self.assertEqual(registro.accion, RegistroAuditoria.Accion.ENROQUE)
        self.assertIn(self.sala_101.nombre, registro.detalle)
        self.assertIn(self.sala_102.nombre, registro.detalle)


class EquiposDeBajaTests(MantencionTestCase):
    def test_equipo_pausado_aparece_en_equipos_de_baja(self):
        self.equipo.activo_en_revision = False
        self.equipo.save(update_fields=['activo_en_revision'])

        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_lista_proyectores'))

        self.assertIn(self.equipo, list(response.context['equipos_de_baja']))

    def test_equipo_activo_no_aparece_en_equipos_de_baja(self):
        self.client.login(username='practicante1', password='clave-segura-123')
        response = self.client.get(reverse('mantencion_lista_proyectores'))

        self.assertNotIn(self.equipo, list(response.context['equipos_de_baja']))
