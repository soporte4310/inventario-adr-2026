def es_adr(request):
    """
    Le dice al navbar de mantención si debe mostrar las secciones
    exclusivas de ADR (roster de equipos, edificios/pisos/salas).
    Un superusuario siempre las ve, igual que en GroupRequiredMixin.
    """
    user = request.user
    if not user.is_authenticated:
        return {'es_adr': False}
    return {'es_adr': user.is_superuser or user.groups.filter(name='ADR').exists()}
