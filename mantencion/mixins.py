from django.contrib.auth.mixins import LoginRequiredMixin


class MantencionLoginRequiredMixin(LoginRequiredMixin):
    """
    Igual que LoginRequiredMixin, pero manda a los usuarios anónimos al
    login propio de Mantención (no al de accounts/inventario). Mantención
    usa las mismas credenciales que el inventario, pero se presenta como
    una plataforma aparte, así que quienes entran por esta 'puerta' deben
    quedarse en ella en vez de terminar en el portal de inventario.
    """
    login_url = 'mantencion_login'
