from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group

from accounts.mixins import GroupRequiredMixin
from .forms import GroupCreateForm


class ListaGruposView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    model = Group
    template_name = 'usuarios/pages/lista_grupos.html'
    context_object_name = 'grupos'
    paginate_by = 20
    group_required = ['ADR']

    def get_queryset(self):
        # user_set y permissions son las relaciones nativas del modelo Group de Django
        queryset = Group.objects.annotate(
            usuarios_count=Count('user', filter=Q(user__is_active=True), distinct=True),
            permisos_count=Count('permissions', distinct=True)
        )

        # 1. Obtener parámetros GET para búsqueda
        search_query = self.request.GET.get('search', '')

        # 2. Aplicar filtros dinámicamente
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_lista'] = 'Roles y Permisos del Sistema'
        
        # Guardar valores actuales para mantener la persistencia en el HTML
        search_query = self.request.GET.get('search', '')
        context['search_query'] = search_query

        # Reconstruir query_string dinámicamente para la paginación de búsquedas
        query_params = []
        if search_query: 
            query_params.append(f'search={search_query}')
        
        context['query_string'] = '&' + '&'.join(query_params) if query_params else ''
        
        return context




class CrearGrupoView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    model = Group
    form_class = GroupCreateForm
    template_name = 'usuarios/pages/agregar_grupo.html'
    success_url = reverse_lazy('lista_grupos')
    # Restricción de seguridad perimetral
    group_required = ['ADR']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_formulario'] = 'Nuevo Rol / Grupo'
        return context