from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, Permission
from collections import defaultdict

from accounts.mixins import GroupRequiredMixin
from .forms import GroupCreateForm, GroupUpdateForm


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


class EditarGrupoView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    model = Group
    form_class = GroupUpdateForm
    template_name = 'usuarios/pages/editar_grupo.html'
    success_url = reverse_lazy('lista_grupos')
    group_required = ['ADR'] # Restricción estricta de seguridad

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_formulario'] = f"Configurar Rol: {self.object.name}"
        
        # 1. Traemos los permisos aplicando la exclusión de lo no deseado
        permisos = Permission.objects.select_related('content_type').exclude(
            # Excluye las apps nativas de administración, sesiones y tipos de contenido
            Q(content_type__app_label__in=['admin', 'contenttypes', 'sessions']) |
            # Excluir de auth
            Q(content_type__app_label='auth', content_type__model='permission')  |
            # Excluir de inventario
            Q(content_type__app_label='inventario', content_type__model='mapeoubicacion') |
            Q(content_type__app_label='inventario', content_type__model='auditoriaactivo', codename__in=['add_auditoriaactivo', 'change_auditoriaactivo']) |
            Q(content_type__app_label='inventario', content_type__model='edificio', codename__in=['add_edificio', 'change_edificio', 'delete_edificio']) |
            Q(content_type__app_label='inventario', content_type__model='piso', codename__in=['add_piso', 'change_piso', 'delete_piso']) |
            Q(content_type__app_label='inventario', content_type__model='estado', codename__in=['add_estado', 'change_estado', 'delete_estado']) |
            # Excluir de accounts
            Q(content_type__app_label='accounts', content_type__model='loginattempt')
        ).order_by('content_type__model', 'codename')
        
        # 2. Agrupamos los permisos por el nombre del modelo
        permisos_agrupados = defaultdict(list)
        for p in permisos:
            nombre_modelo = p.content_type.name.upper()
            
            # Reemplazo simple para la interfaz
            if p.codename.startswith('add_'):
                p.name = f"Crear {p.content_type.name}"
            elif p.codename.startswith('change_'):
                p.name = f"Editar {p.content_type.name}"
            elif p.codename.startswith('delete_'):
                p.name = f"Eliminar {p.content_type.name}"
            elif p.codename.startswith('view_'):
                p.name = f"Ver {p.content_type.name}"
        
            permisos_agrupados[nombre_modelo].append(p)
            
        context['permisos_agrupados'] = dict(permisos_agrupados)
        
        # 3. Pasamos una lista con los IDs de los permisos que ya tiene el grupo actualmente
        context['permisos_actuales_ids'] = list(self.object.permissions.values_list('id', flat=True))
        
        return context

    def form_valid(self, form):
        # Guardamos los cambios del formulario principal (el nombre)
        grupo = form.save(commit=False)
        grupo.save()
        
        # Capturamos la lista de IDs seleccionados desde los checkboxes del HTML
        permisos_seleccionados = self.request.POST.getlist('permisos')
        
        # .set() limpia las relaciones ManyToMany viejas e inyecta las nuevas automáticamente
        grupo.permissions.set(permisos_seleccionados)
        
        return super().form_valid(form)