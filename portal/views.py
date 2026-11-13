from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class PortalIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/pages/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Portal de Sistemas ADR'
        return context