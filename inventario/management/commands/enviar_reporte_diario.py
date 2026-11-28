from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Count

from inventario.models import Activo, AuditoriaActivo
from mantencion.models import RevisionSala, RevisionImpresora, RegistroActividadMantencion

User = get_user_model()


class Command(BaseCommand):
    help = 'Genera y envía el reporte diario consolidado de Inventario y Mantención (últimas 24 horas)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha específica a auditar en formato YYYY-MM-DD (por defecto hoy / últimas 24h).',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Dirección de correo específica para pruebas (omite la lista masiva).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza el envío aunque no existan movimientos ni revisiones registradas.',
        )

    def handle(self, *args, **options):
        ahora = timezone.localtime()
        fecha_param = options.get('fecha')
        email_prueba = options.get('email')
        forzar_envio = options.get('force', False)

        if fecha_param:
            try:
                fecha_obj = datetime.strptime(fecha_param, "%Y-%m-%d").date()
                inicio_ventana = timezone.make_aware(datetime.combine(fecha_obj, datetime.min.time()))
                fin_ventana = timezone.make_aware(datetime.combine(fecha_obj, datetime.max.time()))
            except ValueError:
                self.stderr.write(self.style.ERROR("Formato de fecha inválido. Utilice YYYY-MM-DD."))
                return
        else:
            fin_ventana = ahora
            inicio_ventana = ahora - timedelta(days=1)

        # ----------------------------------------------------
        # 1. DATOS DE INVENTARIO
        # ----------------------------------------------------
        logs_inventario = AuditoriaActivo.objects.filter(
            fecha__gte=inicio_ventana,
            fecha__lte=fin_ventana
        ).select_related('usuario', 'content_type').order_by('-fecha')

        total_activos_sistema = Activo.objects.count()

        # ----------------------------------------------------
        # 2. DATOS DE MANTENCIÓN (SALAS E IMPRESORAS)
        # ----------------------------------------------------
        salas_revisadas = RevisionSala.objects.filter(
            fecha_revision__gte=inicio_ventana,
            fecha_revision__lte=fin_ventana
        ).exclude(
            estado_general=RevisionSala.EstadoGeneralSala.PENDIENTE
        ).select_related(
            'ubicacion__piso__edificio', 
            'operador', 
            'proyector__catalogo__marca'
        ).order_by('-fecha_revision')

        impresoras_revisadas = RevisionImpresora.objects.filter(
            fecha_revision__gte=inicio_ventana,
            fecha_revision__lte=fin_ventana
        ).exclude(
            estado_general=RevisionImpresora.EstadoGeneral.PENDIENTE
        ).select_related(
            'impresora__activo__catalogo__marca',
            'impresora__activo__ubicacion__piso__edificio',
            'operador'
        ).order_by('-fecha_revision')

        # Conteos y focos de atención
        total_salas = salas_revisadas.count()
        salas_criticas = salas_revisadas.filter(estado_general=RevisionSala.EstadoGeneralSala.CRITICA).count()
        salas_obs = salas_revisadas.filter(estado_general=RevisionSala.EstadoGeneralSala.CON_OBSERVACIONES).count()
        salas_operativas = salas_revisadas.filter(estado_general=RevisionSala.EstadoGeneralSala.OPERATIVA).count()

        total_impresoras = impresoras_revisadas.count()
        impresoras_falla = impresoras_revisadas.filter(estado_general=RevisionImpresora.EstadoGeneral.NO_OPERATIVA).count()
        impresoras_operativas = impresoras_revisadas.filter(estado_general=RevisionImpresora.EstadoGeneral.OPERATIVA).count()

        total_alertas_mantencion = salas_criticas + impresoras_falla
        total_movimientos_inv = logs_inventario.count()

        # ----------------------------------------------------
        # 3. VERIFICAR ACTIVIDAD TOTAL
        # ----------------------------------------------------
        hay_actividad = (total_movimientos_inv > 0) or (total_salas > 0) or (total_impresoras > 0)
        if not hay_actividad and not forzar_envio:
            self.stdout.write(self.style.WARNING(
                "Sin movimientos de inventario ni revisiones en la jornada. Envío omitido (use --force para forzar)."
            ))
            return

        # ----------------------------------------------------
        # 4. RANKING UNIFICADO DE COLABORADORES
        # ----------------------------------------------------
        ranking_dict = {}

        # Actividad por inventario
        qs_inv_ranking = AuditoriaActivo.objects.filter(
            fecha__gte=inicio_ventana,
            fecha__lte=fin_ventana,
            usuario__isnull=False
        ).values('usuario_id', 'usuario__first_name', 'usuario__last_name', 'usuario__username').annotate(total=Count('id'))

        for r in qs_inv_ranking:
            u_id = r['usuario_id']
            nombre = f"{r['usuario__first_name']} {r['usuario__last_name']}".strip() or r['usuario__username']
            ranking_dict[u_id] = {
                'nombre': nombre,
                'username': r['usuario__username'],
                'inventario': r['total'],
                'mantencion': 0,
                'total': r['total']
            }

        # Actividad por mantención (registros de auditoría de revisiones)
        qs_mnt_ranking = RegistroActividadMantencion.objects.filter(
            fecha__gte=inicio_ventana,
            fecha__lte=fin_ventana,
            usuario__isnull=False
        ).values('usuario_id', 'usuario__first_name', 'usuario__last_name', 'usuario__username').annotate(total=Count('id'))

        for r in qs_mnt_ranking:
            u_id = r['usuario_id']
            nombre = f"{r['usuario__first_name']} {r['usuario__last_name']}".strip() or r['usuario__username']
            if u_id in ranking_dict:
                ranking_dict[u_id]['mantencion'] += r['total']
                ranking_dict[u_id]['total'] += r['total']
            else:
                ranking_dict[u_id] = {
                    'nombre': nombre,
                    'username': r['usuario__username'],
                    'inventario': 0,
                    'mantencion': r['total'],
                    'total': r['total']
                }

        ranking_unificado = sorted(ranking_dict.values(), key=lambda x: x['total'], reverse=True)[:5]

        # ----------------------------------------------------
        # 5. DESTINATARIOS
        # ----------------------------------------------------
        if email_prueba:
            destinatarios = [email_prueba]
        else:
            destinatarios = list(
                User.objects.filter(is_active=True)
                .exclude(email__isnull=True)
                .exclude(email__exact='')
                .values_list('email', flat=True)
                .distinct()
            )

        if not destinatarios:
            self.stdout.write(self.style.ERROR("No se encontraron destinatarios con correo configurado."))
            return

        # ----------------------------------------------------
        # 6. CONSTRUCCIÓN Y DESPACHO DEL CORREO
        # ----------------------------------------------------
        context = {
            'fecha': ahora.strftime('%d/%m/%Y'),
            'total_activos': total_activos_sistema,
            'total_movimientos_inv': total_movimientos_inv,
            'logs': logs_inventario,
            'total_salas': total_salas,
            'salas_operativas': salas_operativas,
            'salas_obs': salas_obs,
            'salas_criticas': salas_criticas,
            'salas': salas_revisadas,
            'total_impresoras': total_impresoras,
            'impresoras_operativas': impresoras_operativas,
            'impresoras_falla': impresoras_falla,
            'impresoras': impresoras_revisadas,
            'total_alertas_mantencion': total_alertas_mantencion,
            'ranking_unificado': ranking_unificado,
            'portal_url': getattr(settings, 'SITE_URL', 'https://adr.inacap.cl'),
        }

        asunto = f"Sistema ADR - Reporte Diario · {ahora.strftime('%d/%m/%Y')}"
        if total_alertas_mantencion > 0:
            asunto += f" ⚠️ ({total_alertas_mantencion} Foco{'s' if total_alertas_mantencion > 1 else ''} Crítico{'s' if total_alertas_mantencion > 1 else ''})"

        html_content = render_to_string('inventario/emails/reporte_diario.html', context)
        cuerpo_texto = (
            f"REPORTE DIARIO CONSOLIDADO ADR ({context['fecha']})\n\n"
            f"- Movimientos de Inventario: {total_movimientos_inv}\n"
            f"- Salas Revisadas: {total_salas} (Operativas: {salas_operativas}, Con Obs: {salas_obs}, Críticas: {salas_criticas})\n"
            f"- Impresoras Revisadas: {total_impresoras} (Operativas: {impresoras_operativas}, Con Falla: {impresoras_falla})\n"
            f"- Focos que requieren atención: {total_alertas_mantencion}\n\n"
            f"Visualice este informe en formato HTML para consultar el detalle completo."
        )

        remitente = settings.DEFAULT_FROM_EMAIL

        email = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            from_email=remitente,
            to=[remitente],
            bcc=destinatarios
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        self.stdout.write(self.style.SUCCESS(
            f"Reporte diario unificado enviado correctamente a {len(destinatarios)} destinatarios."
        ))