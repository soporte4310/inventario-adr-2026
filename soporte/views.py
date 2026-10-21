from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count
from .models import RegistroListaNegra, FaltaListaNegra
from inventario.models import Funcionario

def lista_negra_view(request):
    """Vista principal para ver y gestionar funcionarios en la lista negra."""
    # Obtenemos expedientes con sus datos relacionados
    expedientes = (
        RegistroListaNegra.objects.select_related('funcionario', 'funcionario__cargo', 'funcionario__area')
        .prefetch_related('faltas')
        .order_by('-fecha_ingreso')
    )
    
    # Funcionarios que aún no están en la lista negra para el <select>
    funcionarios_disponibles = Funcionario.objects.exclude(
        lista_negra__isnull=False
    ).order_by('nombre')

    context = {
        'expedientes': expedientes,
        'funcionarios_disponibles': funcionarios_disponibles,
        'niveles_alerta': RegistroListaNegra.NivelAlerta.choices,
    }
    return render(request, 'soporte/pages/lista_negra.html', context)


def agregar_a_lista_negra(request):
    """Acción POST para fichar a un funcionario."""
    if request.method == 'POST':
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
    
    return redirect('lista_negra')


def eliminar_de_lista_negra(request, pk):
    """Acción POST para indultar/eliminar a un funcionario de la lista."""
    if request.method == 'POST':
        expediente = get_object_or_404(RegistroListaNegra, pk=pk)
        nombre = expediente.funcionario.nombre
        expediente.delete()
        messages.info(request, f"Se ha concedido el indulto a {nombre}. Expediente eliminado.")
    
    return redirect('lista_negra')


def detalle_expediente_view(request, pk):
    """Muestra el expediente del funcionario y su historial de faltas."""
    expediente = get_object_or_404(
        RegistroListaNegra.objects.select_related('funcionario', 'funcionario__cargo', 'funcionario__area')
        .prefetch_related('faltas'),
        pk=pk
    )
    
    context = {
        'expediente': expediente,
        'faltas': expediente.faltas.all(),
        'gravedades': FaltaListaNegra.Gravedad.choices,
    }
    return render(request, 'soporte/pages/detalle_lista_negra.html', context)


def agregar_falta(request, pk):
    """Registra una nueva falta asociada al expediente."""
    if request.method == 'POST':
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
                compensacion=compensacion or "1 paquete de galletas / 1 café para Soporte"
            )
            messages.success(request, f"Falta registrada en el expediente de {expediente.funcionario.nombre}.")
        else:
            messages.error(request, "La descripción del incidente no puede estar vacía.")

    return redirect('detalle_expediente', pk=pk)


def eliminar_falta(request, falta_id):
    """Elimina una falta específica del expediente."""
    if request.method == 'POST':
        falta = get_object_or_404(FaltaListaNegra, pk=falta_id)
        expediente_id = falta.registro.id
        falta.delete()
        messages.info(request, "Falta desestimada y retirada del expediente.")
        return redirect('detalle_expediente', pk=expediente_id)


def reporte_lista_negra_pdf(request):
    """
    Renderiza la plantilla imprimible del reporte oficial consolidado.
    Optimiza la query precalculando la cantidad de faltas por funcionario.
    """
    expedientes = (
        RegistroListaNegra.objects.filter(activo=True)
        .select_related('funcionario', 'funcionario__area', 'funcionario__cargo')
        .annotate(total_faltas=Count('faltas'))
        .order_by('-total_faltas', '-fecha_ingreso')
    )

    context = {
        'expedientes': expedientes,
        'codigo_resolucion': 'RES-EXP-TI-2026/04',
    }
    return render(request, 'soporte/pages/reporte_lista_negra_pdf.html', context)