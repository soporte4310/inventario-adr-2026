from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView, View
from django.db.models import Count

from .models import RegistroListaNegra, FaltaListaNegra
from inventario.models import Funcionario


class ListaNegraView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista principal para listar funcionarios fichados en la lista negra.
    Permite visualizar el registro general y cargar datos para el modal de ingreso.
    """
    model = RegistroListaNegra
    template_name = 'soporte/pages/lista_negra.html'
    context_object_name = 'expedientes'
    permission_required = 'soporte.view_registrolistanegra'

    def get_queryset(self):
        return (
            RegistroListaNegra.objects.select_related(
                'funcionario', 'funcionario__cargo', 'funcionario__area'
            )
            .prefetch_related('faltas')
            .order_by('-fecha_ingreso')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Funcionarios que aún no tienen expediente abierto
        context['funcionarios_disponibles'] = Funcionario.objects.exclude(
            lista_negra__isnull=False
        ).order_by('nombre')
        context['niveles_alerta'] = RegistroListaNegra.NivelAlerta.choices
        return context


class AgregarAListaNegraView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Acción POST para crear un nuevo expediente de lista negra.
    """
    permission_required = 'soporte.add_registrolistanegra'

    def post(self, request, *args, **kwargs):
        funcionario_id = request.POST.get('funcionario_id')
        nivel_alerta = request.POST.get('nivel_alerta', RegistroListaNegra.NivelAlerta.OBSERVACION)
        alias = request.POST.get('alias', '').strip()

        if funcionario_id:
            funcionario = get_object_or_404(Funcionario, pk=funcionario_id)
            RegistroListaNegra.objects.create(
                funcionario=funcionario,
                nivel_alerta=nivel_alerta,
                alias_o_apodo=alias or None
            )
            messages.success(request, f"{funcionario.nombre} ha sido ingresado al registro especial.")
        else:
            messages.error(request, "Debe seleccionar un funcionario válido.")

        return redirect('lista_negra')


class EliminarDeListaNegraView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Acción POST para conceder el indulto y eliminar el expediente de la lista negra.
    """
    permission_required = 'soporte.delete_registrolistanegra'

    def post(self, request, pk, *args, **kwargs):
        expediente = get_object_or_404(RegistroListaNegra, pk=pk)
        nombre = expediente.funcionario.nombre
        expediente.delete()
        messages.info(request, f"Se ha concedido el indulto a {nombre}. Expediente eliminado.")
        return redirect('lista_negra')


class DetalleExpedienteView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Muestra el detalle individual del expediente de un funcionario y el historial de sus faltas.
    """
    model = RegistroListaNegra
    template_name = 'soporte/pages/detalle_lista_negra.html'
    context_object_name = 'expediente'
    permission_required = 'soporte.view_registrolistanegra'

    def get_queryset(self):
        return RegistroListaNegra.objects.select_related(
            'funcionario', 'funcionario__cargo', 'funcionario__area'
        ).prefetch_related('faltas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faltas'] = self.object.faltas.all()
        context['gravedades'] = FaltaListaNegra.Gravedad.choices
        return context


class AgregarFaltaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Acción POST para registrar una falta específica a un expediente existente.
    """
    permission_required = 'soporte.add_faltalistanegra'

    def post(self, request, pk, *args, **kwargs):
        expediente = get_object_or_404(RegistroListaNegra, pk=pk)
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_suceso = request.POST.get('fecha_suceso')
        gravedad = request.POST.get('gravedad', FaltaListaNegra.Gravedad.LEVE)
        compensacion = request.POST.get('compensacion', '').strip()

        if descripcion:
            FaltaListaNegra.objects.create(
                registro=expediente,
                descripcion=descripcion,
                fecha_suceso=fecha_suceso if fecha_suceso else None,
                gravedad=gravedad,
                compensacion=compensacion
            )
            messages.success(request, f"Falta registrada en el expediente de {expediente.funcionario.nombre}.")
        else:
            messages.error(request, "La descripción del incidente no puede estar vacía.")

        return redirect('detalle_expediente', pk=pk)


class EliminarFaltaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Acción POST para desestimar y borrar una falta del historial.
    """
    permission_required = 'soporte.delete_faltalistanegra'

    def post(self, request, falta_id, *args, **kwargs):
        falta = get_object_or_404(FaltaListaNegra, pk=falta_id)
        expediente_id = falta.registro.id
        falta.delete()
        messages.info(request, "Falta desestimada y retirada del expediente.")
        return redirect('detalle_expediente', pk=expediente_id)


class ReporteListaNegraPDFView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Renderiza la plantilla oficial optimizada para guardado/impresión en PDF.
    """
    template_name = 'soporte/pages/reporte_lista_negra_pdf.html'
    permission_required = 'soporte.view_registrolistanegra'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expedientes'] = (
            RegistroListaNegra.objects.filter(activo=True)
            .select_related('funcionario', 'funcionario__area', 'funcionario__cargo')
            .annotate(total_faltas=Count('faltas'))
            .order_by('-total_faltas', '-fecha_ingreso')
        )
        context['codigo_resolucion'] = 'RES-EXP-TI-2026/04'
        return context