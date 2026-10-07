"""
Utilidades compartidas entre 'enviar_reporte_diario' y 'enviar_reporte_semanal'.
No es un management command (por eso el guión bajo): Django lo ignora al listar comandos.
"""
from django.db.models import Count


def ranking_actividad(logs_qs, limite=5):
    """
    Calcula el top de usuarios con más acciones dentro del queryset de AuditoriaActivo dado.
    Devuelve una lista de dicts: nombre, cantidad y porcentaje relativo al usuario más activo.
    """
    ranking_qs = logs_qs.values(
        'usuario__first_name', 'usuario__last_name', 'usuario__username'
    ).annotate(total=Count('id')).order_by('-total')

    stats_usuarios = []
    if ranking_qs.exists():
        max_acciones = ranking_qs[0]['total']
        for entry in ranking_qs[:limite]:
            nombre = f"{entry['usuario__first_name']} {entry['usuario__last_name']}".strip() or entry['usuario__username']
            stats_usuarios.append({
                'nombre': nombre,
                'cantidad': entry['total'],
                'porcentaje': int((entry['total'] / max_acciones) * 100),
            })
    return stats_usuarios


def resumen_por_accion(logs_qs):
    """Cuenta creaciones, modificaciones, eliminaciones y restauraciones dentro del queryset dado."""
    return {
        'creados': logs_qs.filter(accion='CRE').count(),
        'editados': logs_qs.filter(accion='MOD').count(),
        'eliminados': logs_qs.filter(accion='ELI').count(),
        'restaurados': logs_qs.filter(accion='RES').count(),
    }
