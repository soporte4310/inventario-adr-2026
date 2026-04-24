from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class GroupRequiredMixin(UserPassesTestMixin):
    """
    Mixin que permite el acceso solo a usuarios en grupos específicos.
    Uso: group_required = ['ADR', 'Alumno en Práctica', 'Auxiliar Operador ADR', 'Operador ADR']
    """
    group_required = None

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        
        if self.group_required is None:
            return True
            
        return self.request.user.groups.filter(name__in=self.group_required).exists()

    def handle_no_permission(self):
        # Si no tiene permiso, lanzamos un 403 en lugar de redirigir al login
        raise PermissionDenied