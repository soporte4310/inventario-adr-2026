from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from datetime import timedelta
from ...models import Activo, AuditoriaActivo
from django.conf import settings
from django.db.models import Count

User = get_user_model()

class Command(BaseCommand):
    help = 'Envía el detalle de cambios de las últimas 24 horas'

    def handle(self, *args, **options):
        ahora = timezone.now()
        hace_24h = ahora - timedelta(days=1)
        
        # 1. OBTENER TODA LA AUDITORÍA DEL DÍA
        # Seleccionamos los campos necesarios y el objeto relacionado
        logs = AuditoriaActivo.objects.filter(
            fecha__gte=hace_24h
        ).select_related('usuario', 'content_type').order_by('-fecha')

        # 2. TOTAL DE ACTIVOS PARA EL HEADER
        total_activos = Activo.objects.count()

        # --- GRÁFICO DE ACTIVIDAD ---
        ranking_qs = AuditoriaActivo.objects.filter(fecha__gte=hace_24h)\
            .values('usuario__first_name', 'usuario__last_name', 'usuario__username')\
            .annotate(total=Count('id'))\
            .order_by('-total')

        stats_usuarios = []
        if ranking_qs.exists():
            max_acciones = ranking_qs[0]['total']
            for entry in ranking_qs[:5]:
                nombre = f"{entry['usuario__first_name']} {entry['usuario__last_name']}".strip() or entry['usuario__username']
                stats_usuarios.append({
                    'nombre': nombre,
                    'cantidad': entry['total'],
                    'porcentaje': int((entry['total'] / max_acciones) * 100)
                })

        # 3. DESTINATARIOS
        emails = list(User.objects.filter(is_active=True).values_list('email', flat=True))

        if not logs.exists():
            self.stdout.write("Sin movimientos en las últimas 24h. No se envía reporte.")
            return

        context = {
            'fecha': ahora.strftime('%d/%m/%Y'),
            'logs': logs,
            'total_activos': total_activos,
            'stats_usuarios': stats_usuarios,
        }

        html_content = render_to_string('inventario/emails/reporte_diario.html', context)
        
        email = EmailMultiAlternatives(
            subject=f"Reporte Diario - {ahora.strftime('%d/%m/%Y')}",
            body="Revisar en modo HTML",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails,
        )
        email.attach_alternative(html_content, "text/html")
        email.send()