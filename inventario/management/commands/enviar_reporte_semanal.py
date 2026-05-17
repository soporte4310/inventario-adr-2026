from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db.models import Count, Q
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.conf import settings
from ...models import Activo, AuditoriaActivo, Categoria, Estado, Ubicacion
from adr.models import Prestamo

User = get_user_model()

class Command(BaseCommand):
    help = 'Genera y envía el dashboard semanal avanzado a todos los usuarios'

    def handle(self, *args, **options):
        hoy = timezone.now()
        hace_una_semana = hoy - timedelta(days=7)
        limite_prestamo = hoy - timedelta(days=3) # Alerta si lleva > 3 días

        # 1. DEFINIR UBICACIONES DE INTERÉS
        nombres_ubicaciones = [
            "Auditorio", "Azotea", "Bodega ADR", 
            "Oficina ADR", "Bodega Central", "Bodega Patio"
        ]

        # 2. CONSULTA OPTIMIZADA POR UBICACIÓN
        # Usamos iexact para evitar problemas con mayúsculas/minúsculas
        resumen_ubicaciones = Ubicacion.objects.filter(
            nombre__in=nombres_ubicaciones
        ).annotate(
            total_operativos=Count('activo', filter=Q(
                activo__is_deleted=False, 
                activo__estado__nombre__iexact='Operativo'
            )),
            total_danados=Count('activo', filter=Q(
                activo__is_deleted=False, 
                activo__estado__nombre__iexact='Dañado'
            )),
            total_baja=Count('activo', filter=Q(
                activo__is_deleted=False, 
                activo__estado__nombre__iexact='De Baja'
            ))
        ).order_by('nombre')

        # 3. MÉTRICAS DE INVENTARIO (ESTADOS)
        estados_resumen = Estado.objects.annotate(
            total=Count('activo', filter=Q(activo__is_deleted=False))
        ).order_by('-total')

        # 4. CATEGORÍAS CON DETALLE
        resumen_categorias = Categoria.objects.annotate(
            total=Count('catalogo__activo', filter=Q(catalogo__activo__is_deleted=False))
        ).order_by('-total')

        # 5. ALERTAS DE PRÉSTAMOS CRÍTICOS
        prestamos_criticos = Prestamo.objects.filter(
            estado='En Préstamo',
            fecha_prestamo__lte=limite_prestamo
        ).order_by('fecha_prestamo')

        # 6. ACTIVIDAD DE AUDITORÍA
        auditoria = {
            'creados': AuditoriaActivo.objects.filter(accion='CRE', fecha__gte=hace_una_semana).count(),
            'editados': AuditoriaActivo.objects.filter(accion='MOD', fecha__gte=hace_una_semana).count(),
            'eliminados': AuditoriaActivo.objects.filter(accion='ELI', fecha__gte=hace_una_semana).count(),
        }

        # 7. OBTENER DESTINATARIOS (Usuarios activos)
        emails_destinatarios = list(User.objects.filter(is_active=True).values_list('email', flat=True))
        emails_destinatarios = [e for e in emails_destinatarios if e] # Filtrar nulos

        total_activos_vivos = Activo.objects.count()

        # 8. RENDER Y ENVÍO
        context = {
            'fecha': hoy.strftime('%d/%m/%Y'),
            'total_activos': total_activos_vivos,
            'estados': estados_resumen,
            'categorias': resumen_categorias,
            'alertas': prestamos_criticos,
            'auditoria': auditoria,
            'total_activos': Activo.objects.count(),
            'resumen_ubicaciones': resumen_ubicaciones,
        }

        html_content = render_to_string('inventario/emails/reporte_semanal.html', context)
        
        email = EmailMultiAlternatives(
            subject=f"Reporte Semanal: Estado del Inventario",
            body="Favor visualizar en modo HTML",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails_destinatarios,
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        self.stdout.write(self.style.SUCCESS(f'Reporte enviado a {len(emails_destinatarios)} usuarios.'))