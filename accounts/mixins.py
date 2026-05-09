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
            
        # Verificar si está autenticado aquí también para evitar errores
        if not self.request.user.is_authenticated:
            return False
            
        return self.request.user.groups.filter(name__in=self.group_required).exists()

    def handle_no_permission(self):
        # Si el usuario NO está logueado, que LoginRequiredMixin o AccessMixin manejen la redirección
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        
        # Si está logueado pero llegó aquí, es porque test_func falló (no tiene el grupo)
        raise PermissionDenied