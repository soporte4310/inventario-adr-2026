from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db.models import Count, Q
from collections import Counter
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.conf import settings
from ...models import Activo, AuditoriaActivo, Categoria, Estado, Ubicacion
from adr.models import Prestamo
from ._reportes_utils import ranking_actividad, resumen_por_accion

User = get_user_model()

DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

ETIQUETAS_COMPARATIVO = {
    'creados': 'Activos creados',
    'editados': 'Activos editados',
    'eliminados': 'Activos eliminados',
    'restaurados': 'Activos restaurados',
}


class Command(BaseCommand):
    help = 'Genera y envía la recapitulación semanal del inventario, comparada con la semana anterior'

    def handle(self, *args, **options):
        hoy = timezone.now()
        inicio_semana_actual = hoy - timedelta(days=7)
        inicio_semana_anterior = hoy - timedelta(days=14)
        limite_prestamo = hoy - timedelta(days=3)  # Alerta si lleva > 3 días

        # 1. DEFINIR UBICACIONES DE INTERÉS
        nombres_ubicaciones = [
            "Auditorio", "Azotea", "Bodega ADR",
            "Oficina ADR", "Bodega Central", "Bodega Patio"
        ]

        # 2. CONSULTA OPTIMIZADA POR UBICACIÓN (estado actual)
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

        # 3. MÉTRICAS DE INVENTARIO (ESTADOS, estado actual)
        estados_resumen = Estado.objects.annotate(
            total=Count('activo', filter=Q(activo__is_deleted=False))
        ).order_by('-total')

        # 4. CATEGORÍAS CON DETALLE (estado actual)
        resumen_categorias = Categoria.objects.annotate(
            total=Count('catalogo__activo', filter=Q(catalogo__activo__is_deleted=False))
        ).order_by('-total')

        # 5. ALERTAS DE PRÉSTAMOS CRÍTICOS (estado actual)
        prestamos_criticos = Prestamo.objects.filter(
            estado='En Préstamo',
            fecha_prestamo__lte=limite_prestamo
        ).order_by('fecha_prestamo')

        # 6. AUDITORÍA: SEMANA ACTUAL VS. SEMANA ANTERIOR (recapitulación)
        logs_semana_actual_base = AuditoriaActivo.objects.filter(
            fecha__gte=inicio_semana_actual, fecha__lt=hoy
        )
        logs_semana_anterior_base = AuditoriaActivo.objects.filter(
            fecha__gte=inicio_semana_anterior, fecha__lt=inicio_semana_actual
        )

        auditoria_actual = resumen_por_accion(logs_semana_actual_base)
        auditoria_anterior = resumen_por_accion(logs_semana_anterior_base)

        comparativo = []
        for clave, etiqueta in ETIQUETAS_COMPARATIVO.items():
            actual = auditoria_actual[clave]
            anterior = auditoria_anterior[clave]
            diferencia = actual - anterior
            comparativo.append({
                'etiqueta': etiqueta,
                'actual': actual,
                'anterior': anterior,
                'diferencia': diferencia,
                'tendencia': 'subio' if diferencia > 0 else ('bajo' if diferencia < 0 else 'igual'),
            })

        # Préstamos gestionados: semana actual vs. semana anterior
        prestamos_actual = Prestamo.objects.filter(
            fecha_prestamo__gte=inicio_semana_actual, fecha_prestamo__lt=hoy
        ).count()
        prestamos_anterior = Prestamo.objects.filter(
            fecha_prestamo__gte=inicio_semana_anterior, fecha_prestamo__lt=inicio_semana_actual
        ).count()
        diferencia_prestamos = prestamos_actual - prestamos_anterior
        comparativo.append({
            'etiqueta': 'Préstamos registrados',
            'actual': prestamos_actual,
            'anterior': prestamos_anterior,
            'diferencia': diferencia_prestamos,
            'tendencia': 'subio' if diferencia_prestamos > 0 else ('bajo' if diferencia_prestamos < 0 else 'igual'),
        })

        # 7. RANKING DE ACTIVIDAD SEMANAL + usuario más activo de la semana pasada (comparación)
        stats_usuarios = ranking_actividad(logs_semana_actual_base)
        top_anterior = ranking_actividad(logs_semana_anterior_base, limite=1)
        usuario_mas_activo_anterior = top_anterior[0] if top_anterior else None

        # 8. ACTIVIDAD POR DÍA DE LA SEMANA (para la recapitulación detallada)
        # Se agrupa en Python (no con TruncDate) porque MySQL sin tablas de zona horaria
        # instaladas devuelve NULL al truncar fechas con USE_TZ=True.
        conteo_por_dia = Counter(
            timezone.localtime(fecha).date()
            for fecha in logs_semana_actual_base.values_list('fecha', flat=True)
        )
        actividad_diaria = [
            {'fecha': dia, 'dia_semana': DIAS_ES[dia.weekday()], 'total': total}
            for dia, total in sorted(conteo_por_dia.items())
        ]

        # 9. DETALLE COMPLETO DE MOVIMIENTOS DE LA SEMANA (misma estructura que el reporte diario)
        logs_semana_actual = logs_semana_actual_base.select_related(
            'usuario', 'content_type'
        ).order_by('-fecha')

        # 10. DESTINATARIOS (Usuarios activos)
        emails_destinatarios = list(User.objects.filter(is_active=True).values_list('email', flat=True))
        emails_destinatarios = [e for e in emails_destinatarios if e]  # Filtrar nulos

        total_activos_vivos = Activo.objects.count()

        # 11. RENDER Y ENVÍO
        context = {
            'fecha': hoy.strftime('%d/%m/%Y'),
            'inicio_semana': inicio_semana_actual.strftime('%d/%m/%Y'),
            'fin_semana': hoy.strftime('%d/%m/%Y'),
            'total_activos': total_activos_vivos,
            'estados': estados_resumen,
            'categorias': resumen_categorias,
            'alertas': prestamos_criticos,
            'resumen_ubicaciones': resumen_ubicaciones,
            'comparativo': comparativo,
            'stats_usuarios': stats_usuarios,
            'usuario_mas_activo_anterior': usuario_mas_activo_anterior,
            'actividad_diaria': actividad_diaria,
            'logs': logs_semana_actual,
        }

        html_content = render_to_string('inventario/emails/reporte_semanal.html', context)

        email = EmailMultiAlternatives(
            subject=f"Reporte Semanal: Estado del Inventario ({context['inicio_semana']} - {context['fin_semana']})",
            body="Favor visualizar en modo HTML",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails_destinatarios,
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        self.stdout.write(self.style.SUCCESS(f'Reporte enviado a {len(emails_destinatarios)} usuarios.'))
