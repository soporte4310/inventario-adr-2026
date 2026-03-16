"""
Vistas para equipos - TODOS LOS MODELOS refactorizados

Este módulo contiene las vistas CRUD refactorizadas para TODOS los modelos de equipos,
usando las clases base genéricas de base.py.
"""

from django.urls import reverse_lazy

from adr.models import (
    AllInOne, AllInOneAdmins, Notebook, MiniPC, Proyectores,
    BodegaADR, Azotea, Monitor, Audio, Tablet,
    EquiposIsla, SwitchDeRed, Televisor
)
from adr.forms import (
    AllInOneForm, AllInOneAdminsForm, NotebooksForm, MiniPCForm,
    ProyectoresForm, BodegaADRForm, AzoteaForm, MonitorForm,
    AudioForm, TabletForm, EquiposIslaForm, SwitchDeRedForm, TelevisorForm
)
from .base import ActivoListView, ActivoCreateView, ActivoUpdateView, ActivoDetailView


# ==================== ALL IN ONE ====================

class AllInOneListView(ActivoListView):
    model = AllInOne
    template_name = 'modulos/all_in_one.html'
    context_object_name = 'all_in_ones'

class AllInOneCreateView(ActivoCreateView):
    model = AllInOne
    template_name = './modulos/add_all_in_one.html'
    form_class = AllInOneForm
    success_url = reverse_lazy('all_in_one')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class AllInOneUpdateView(ActivoUpdateView):
    model = AllInOne
    template_name = 'modulos/edit_all_in_one.html'
    form_class = AllInOneForm
    success_url = reverse_lazy('all_in_one')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class AllInOneDetailView(ActivoDetailView):
    model = AllInOne
    template_name = 'modulos/detalle_all_in_one.html'
    context_object_name = 'all_in_one'


# ==================== ALL IN ONE ADMINS ====================

class AllInOneAdminListView(ActivoListView):
    model = AllInOneAdmins
    template_name = 'modulos/all_in_one_adm.html'
    context_object_name = 'all_in_ones_admins'

class AllInOneAdminCreateView(ActivoCreateView):
    model = AllInOneAdmins
    template_name = './modulos/add_all_in_one_adm.html'
    form_class = AllInOneAdminsForm
    success_url = reverse_lazy('all_in_one_adm')
    allowed_groups = ['ADR', 'Operadores ADR']

class AllInOneAdminUpdateView(ActivoUpdateView):
    model = AllInOneAdmins
    template_name = 'modulos/edit_all_in_one_adm.html'
    form_class = AllInOneAdminsForm
    success_url = reverse_lazy('all_in_one_adm')
    allowed_groups = ['ADR', 'Operadores ADR']


# ==================== NOTEBOOKS ====================

class NotebookListView(ActivoListView):
    model = Notebook
    template_name = 'modulos/notebooks.html'
    context_object_name = 'notebooks'

class NotebookCreateView(ActivoCreateView):
    model = Notebook
    template_name = 'modulos/add_notebooks.html'
    form_class = NotebooksForm
    success_url = reverse_lazy('notebooks')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class NotebookUpdateView(ActivoUpdateView):
    model = Notebook
    template_name = 'modulos/edit_notebooks.html'
    form_class = NotebooksForm
    success_url = reverse_lazy('notebooks')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class NotebookDetailView(ActivoDetailView):
    model = Notebook
    template_name = 'modulos/detalle_notebook.html'
    context_object_name = 'notebook'


# ==================== MINI PC ====================

class MiniPCListView(ActivoListView):
    model = MiniPC
    template_name = 'modulos/mini_pc.html'
    context_object_name = 'mini_pcs'

class MiniPCCreateView(ActivoCreateView):
    model = MiniPC
    template_name = 'modulos/add_mini_pc.html'
    form_class = MiniPCForm
    success_url = reverse_lazy('mini_pc')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class MiniPCUpdateView(ActivoUpdateView):
    model = MiniPC
    template_name = 'modulos/edit_mini_pc.html'
    form_class = MiniPCForm
    success_url = reverse_lazy('mini_pc')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class MiniPCDetailView(ActivoDetailView):
    model = MiniPC
    template_name = 'modulos/detalle_mini_pc.html'
    context_object_name = 'mini_pc'


# ==================== PROYECTORES ====================

class ProyectorListView(ActivoListView):
    model = Proyectores
    template_name = 'modulos/proyectores.html'
    context_object_name = 'proyectores'

class ProyectorCreateView(ActivoCreateView):
    model = Proyectores
    template_name = 'modulos/add_proyector.html'
    form_class = ProyectoresForm
    success_url = reverse_lazy('proyector')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class ProyectorUpdateView(ActivoUpdateView):
    model = Proyectores
    template_name = 'modulos/edit_proyector.html'
    form_class = ProyectoresForm
    success_url = reverse_lazy('proyector')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class ProyectorDetailView(ActivoDetailView):
    model = Proyectores
    template_name = 'modulos/detalle_proyector.html'
    context_object_name = 'proyector'


# ==================== BODEGA ADR ====================

class BodegaADRListView(ActivoListView):
    model = BodegaADR
    template_name = 'modulos/bodega_adr.html'
    context_object_name = 'bodegas_adr'  # Plural - requerido por template

class BodegaADRCreateView(ActivoCreateView):
    model = BodegaADR
    template_name = 'modulos/add_bodega_adr.html'
    form_class = BodegaADRForm
    success_url = reverse_lazy('bodega_adr')
    allowed_groups = ['ADR', 'Operadores ADR']

class BodegaADRUpdateView(ActivoUpdateView):
    model = BodegaADR
    template_name = 'modulos/edit_bodega_adr.html'
    form_class = BodegaADRForm
    success_url = reverse_lazy('bodega_adr')
    allowed_groups = ['ADR', 'Operadores ADR']

class BodegaADRDetailView(ActivoDetailView):
    model = BodegaADR
    template_name = 'modulos/detalle_bodegaadr.html'
    context_object_name = 'bodega_item'


# ==================== AZOTEA ====================

class AzoteaListView(ActivoListView):
    model = Azotea
    template_name = 'modulos/azotea_adr.html'
    context_object_name = 'azoteas_adr'  # Match original legacy views

class AzoteaCreateView(ActivoCreateView):
    model = Azotea
    template_name = 'modulos/add_azotea.html'
    form_class = AzoteaForm
    success_url = reverse_lazy('azotea')
    allowed_groups = ['ADR', 'Operadores ADR']

class AzoteaUpdateView(ActivoUpdateView):
    model = Azotea
    template_name = 'modulos/edit_azotea.html'
    form_class = AzoteaForm
    success_url = reverse_lazy('azotea')
    allowed_groups = ['ADR', 'Operadores ADR']

class AzoteaDetailView(ActivoDetailView):
    model = Azotea
    template_name = 'modulos/detalle_azotea.html'
    context_object_name = 'azotea'


# ==================== MONITORES ====================

class MonitorListView(ActivoListView):
    model = Monitor
    template_name = 'modulos/monitor.html'
    context_object_name = 'monitores'

class MonitorCreateView(ActivoCreateView):
    model = Monitor
    template_name = 'modulos/add_monitor.html'
    form_class = MonitorForm
    success_url = reverse_lazy('monitor')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class MonitorUpdateView(ActivoUpdateView):
    model = Monitor
    template_name = 'modulos/edit_monitor.html'
    form_class = MonitorForm
    success_url = reverse_lazy('monitor')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class MonitorDetailView(ActivoDetailView):
    model = Monitor
    template_name = 'modulos/detalle_monitor.html'
    context_object_name = 'monitor'


# ==================== AUDIO ====================

class AudioListView(ActivoListView):
    model = Audio
    template_name = 'modulos/audio.html'
    context_object_name = 'audios'

class AudioCreateView(ActivoCreateView):
    model = Audio
    template_name = 'modulos/add_audio.html'
    form_class = AudioForm
    success_url = reverse_lazy('audio')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class AudioUpdateView(ActivoUpdateView):
    model = Audio
    template_name = 'modulos/edit_audio.html'
    form_class = AudioForm
    success_url = reverse_lazy('audio')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class AudioDetailView(ActivoDetailView):
    model = Audio
    template_name = 'modulos/detalle_audio.html'
    context_object_name = 'audio'


# ==================== TABLETS ====================

class TabletListView(ActivoListView):
    model = Tablet
    template_name = 'modulos/tablet.html'
    context_object_name = 'tablets'

class TabletCreateView(ActivoCreateView):
    model = Tablet
    template_name = 'modulos/add_tablet.html'
    form_class = TabletForm
    success_url = reverse_lazy('tablet')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class TabletUpdateView(ActivoUpdateView):
    model = Tablet
    template_name = 'modulos/edit_tablet.html'
    form_class = TabletForm
    success_url = reverse_lazy('tablet')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class TabletDetailView(ActivoDetailView):
    model = Tablet
    template_name = 'modulos/detalle_tablet.html'
    context_object_name = 'tablet'


# ==================== EQUIPOS ISLA ====================

class EquiposIslaListView(ActivoListView):
    model = EquiposIsla
    template_name = 'modulos/equipos_isla.html'
    context_object_name = 'equipos_isla'

class EquiposIslaCreateView(ActivoCreateView):
    model = EquiposIsla
    template_name = 'modulos/add_equipos_isla.html'
    form_class = EquiposIslaForm
    success_url = reverse_lazy('equipos_isla')
    allowed_groups = ['ADR', 'Operadores ADR']

class EquiposIslaUpdateView(ActivoUpdateView):
    model = EquiposIsla
    template_name = 'modulos/edit_equipos_isla.html'
    form_class = EquiposIslaForm
    success_url = reverse_lazy('equipos_isla')
    allowed_groups = ['ADR', 'Operadores ADR']

class EquiposIslaDetailView(ActivoDetailView):
    model = EquiposIsla
    template_name = 'modulos/detalle_equipos_isla.html'
    context_object_name = 'equipo_isla'


# ==================== SWITCH DE RED ====================

class SwitchDeRedListView(ActivoListView):
    model = SwitchDeRed
    template_name = 'modulos/switch_de_red.html'
    context_object_name = 'switch_de_red'  # Match legacy template expectations

class SwitchDeRedCreateView(ActivoCreateView):
    model = SwitchDeRed
    template_name = 'modulos/add_switch_de_red.html'
    form_class = SwitchDeRedForm
    success_url = reverse_lazy('switch_de_red')
    allowed_groups = ['ADR', 'Operadores ADR']

class SwitchDeRedUpdateView(ActivoUpdateView):
    model = SwitchDeRed
    template_name = 'modulos/edit_switch_de_red.html'
    form_class = SwitchDeRedForm
    success_url = reverse_lazy('switch_de_red')
    allowed_groups = ['ADR', 'Operadores ADR']

class SwitchDeRedDetailView(ActivoDetailView):
    model = SwitchDeRed
    template_name = 'modulos/detalle_switch_de_red.html'
    context_object_name = 'switch_de_red'


# ==================== TELEVISOR ====================

class TelevisorListView(ActivoListView):
    model = Televisor
    template_name = 'modulos/televisor.html'
    context_object_name = 'televisores'

class TelevisorCreateView(ActivoCreateView):
    model = Televisor
    template_name = 'modulos/add_televisor.html'
    form_class = TelevisorForm
    success_url = reverse_lazy('televisor')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class TelevisorUpdateView(ActivoUpdateView):
    model = Televisor
    template_name = 'modulos/edit_televisor.html'
    form_class = TelevisorForm
    success_url = reverse_lazy('televisor')
    allowed_groups = ['ADR', 'Operadores ADR', 'Auxiliares Operadores ADR']

class TelevisorDetailView(ActivoDetailView):
    model = Televisor
    template_name = 'modulos/detalle_televisor.html'
    context_object_name = 'televisor'
