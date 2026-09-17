import os
from collections import OrderedDict

from django import forms
from django.db.models import Q

from inventario.models import Activo, Ubicacion

from .models import EquipoMantenible, EvidenciaRevision, Impresora


def _agrupar_ubicaciones_por_edificio_y_piso(field, queryset=None):
    """
    Reemplaza las opciones de un ModelChoiceField de Ubicacion por una lista
    agrupada en <optgroup> "Edificio · Piso" (ej: "Edificio A · Piso 1"),
    para que sea fácil ubicar la sala correcta entre más de un centenar de
    opciones. HTML no soporta un segundo nivel de agrupación (Edificio >
    Piso), así que combinamos ambos en la misma etiqueta.

    Las bodegas (donde va un equipo que se retira de una sala, ej. "Bodega
    ADR") quedan en un grupo aparte al principio de la lista, para no tener
    que buscarlas entre los edificios cuando alguien devuelve un equipo.

    Esto sólo cambia cómo se VE el campo: la validación real sigue usando
    field.queryset (ModelChoiceField.clean no consulta .choices).
    """
    queryset = queryset if queryset is not None else field.queryset
    ubicaciones = queryset.select_related('piso__edificio').order_by(
        'piso__edificio__nombre', 'piso__nombre', 'nombre'
    )

    bodegas = []
    grupos = OrderedDict()
    for ubicacion in ubicaciones:
        if 'bodega' in ubicacion.nombre.lower():
            bodegas.append((ubicacion.pk, ubicacion.nombre))
            continue
        etiqueta_grupo = f"{ubicacion.piso.edificio.nombre} · {ubicacion.piso.nombre}"
        grupos.setdefault(etiqueta_grupo, []).append((ubicacion.pk, ubicacion.nombre))

    choices = [('', field.empty_label)] if field.empty_label is not None else []
    if bodegas:
        choices.append(('Disponible / Bodega', bodegas))
    choices += list(grupos.items())
    field.choices = choices


class UbicacionAgrupadaField(forms.ModelChoiceField):
    """
    ModelChoiceField de Ubicacion con las opciones agrupadas por
    Edificio/Piso/Bodega. Ojo: las opciones se recalculan en __deepcopy__,
    no en __init__, porque __init__ sólo corre UNA vez (al importar el
    módulo, cuando se evalúa "ubicacion = UbicacionAgrupadaField(...)" en
    el cuerpo de cada formulario). Django clona los campos declarados con
    deepcopy() por cada instancia de formulario (o sea, en cada request),
    así que ahí es donde hay que consultar la BD de nuevo para no quedarnos
    con la foto de ubicaciones que existía cuando arrancó el servidor.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('queryset', Ubicacion.objects.select_related('piso__edificio').all())
        kwargs.setdefault('widget', forms.Select(attrs={'class': 'form-control'}))
        super().__init__(*args, **kwargs)
        _agrupar_ubicaciones_por_edificio_y_piso(self)

    def __deepcopy__(self, memo):
        resultado = super().__deepcopy__(memo)
        _agrupar_ubicaciones_por_edificio_y_piso(resultado)
        return resultado


class AgregarProyectorForm(forms.ModelForm):
    """
    Formulario (sólo ADR) para inscribir un Activo YA inventariado como
    proyector en el circuito de mantención. No crea activos nuevos: sólo
    elige uno existente de 'inventario' (los proyectores siguen siendo
    Activos reales; a diferencia de las impresoras, que no lo son).

    El campo 'ubicacion' es opcional y no pertenece al modelo EquipoMantenible:
    si se completa, la vista lo usa para corregir/confirmar de una vez el
    edificio/sala del Activo real (mismo mecanismo que el 'enroque').
    """
    ubicacion = UbicacionAgrupadaField(
        required=False,
        empty_label="-- Mantener la ubicación actual del inventario --",
        label="Confirmar sala/oficina (opcional)"
    )

    class Meta:
        model = EquipoMantenible
        fields = ['activo']
        widgets = {
            'activo': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.tipo = EquipoMantenible.Tipo.PROYECTOR

        # Sólo ofrecemos activos que todavía no estén en el roster (el
        # enlace es OneToOne) y que sean de categoría "Proyector".
        ya_inscritos = EquipoMantenible.objects.filter(
            activo__isnull=False
        ).values_list('activo_id', flat=True)
        self.fields['activo'].queryset = Activo.objects.filter(
            Q(catalogo__categoria__nombre__icontains='proyector')
        ).exclude(pk__in=ya_inscritos).select_related('catalogo__categoria', 'catalogo__marca')

    def clean_activo(self):
        # No tiene sentido meter a mantención mensual un equipo que el
        # inventario ya marcó como dañado, de baja, en mantención externa o
        # prestado: podría confundir al practicante o duplicar trabajo con
        # el encargado de inventario. Sólo se admite si está Operativo.
        activo = self.cleaned_data['activo']
        if activo.estado and activo.estado.nombre.strip().upper() != 'OPERATIVO':
            raise forms.ValidationError(
                f"No se puede agregar: este equipo figura como \"{activo.estado.nombre}\" en el inventario "
                "(no Operativo). Corrobora el estado con el encargado de inventario antes de inscribirlo."
            )
        return activo


class ImpresoraForm(forms.ModelForm):
    """
    Formulario (sólo ADR) para agregar una impresora NUEVA al circuito de
    mantención. A diferencia de los proyectores, las impresoras no vienen
    de 'inventario' (son del proveedor externo), así que aquí se cargan
    sus datos directamente en vez de elegir un Activo ya existente.
    """
    ubicacion = UbicacionAgrupadaField(required=False, empty_label="-- Sin asignar todavía --")

    class Meta:
        model = Impresora
        fields = [
            'marca', 'modelo', 'tipo_impresion', 'rango_impresiones',
            'nombre_equipo', 'numero_serie', 'ip', 'mac', 'codigo_proveedor', 'ubicacion',
        ]
        widgets = {
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: E42540'}),
            'tipo_impresion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Blanco y Negro'}),
            'rango_impresiones': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1500 - 7500'}),
            'nombre_equipo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: IQQ_E540_BODEGA'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            'ip': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 172.16.5.157'}),
            'mac': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_proveedor': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EliminarImpresoraForm(forms.Form):
    """
    "Dar de baja" una impresora (ej: se rompió y la reemplazaron por una
    nueva). No borra nada: marca la Impresora como De Baja/Deprecada y
    pausa su EquipoMantenible, dejando el historial intacto para siempre.
    """
    impresora = forms.ModelChoiceField(
        queryset=Impresora.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Impresora a dar de baja",
        empty_label="-- Selecciona una impresora --"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['impresora'].queryset = Impresora.objects.filter(
            estado=Impresora.EstadoImpresora.OPERATIVA
        ).order_by('modelo', 'nombre_equipo')


class NovedadRevisionForm(forms.Form):
    """
    Formulario que usa el practicante en terreno cuando un equipo NO está
    bien: describe qué pasó y adjunta una foto o un video como evidencia.
    """
    comentario = forms.CharField(
        label="¿Qué le pasó al equipo?",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ej: No enciende, falta control remoto, atasco de papel...'})
    )
    archivo = forms.FileField(
        label="Foto o video de evidencia",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*,video/*', 'capture': 'environment'})
    )

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        # La extensión decide el camino de procesamiento: las fotos se
        # comprimen con el pipeline de Pillow ya existente; los videos se
        # validan (tipo/peso) y se suben tal cual, sin transcodificar.
        ext = os.path.splitext(archivo.name)[1].lower()

        if ext in ('.jpg', '.jpeg', '.png', '.webp'):
            self.tipo_archivo = EvidenciaRevision.TipoArchivo.FOTO
        elif ext == '.mp4':
            from common.validators import validar_video
            validar_video(archivo)
            self.tipo_archivo = EvidenciaRevision.TipoArchivo.VIDEO
        else:
            raise forms.ValidationError("Formato no soportado. Usa JPG, PNG, WEBP (foto) o MP4 (video).")

        return archivo


class EnroqueActivoForm(forms.ModelForm):
    """
    El 'enroque' de un proyector: reasigna la sala/oficina de su Activo.
    Al guardar, el cambio queda auditado automáticamente por las señales
    de 'inventario'.
    """
    ubicacion = UbicacionAgrupadaField(empty_label="-- Buscar nueva ubicación... --")

    class Meta:
        model = Activo
        fields = ['ubicacion']


class EnroqueImpresoraForm(forms.ModelForm):
    """El 'enroque' de una impresora: reasigna directamente Impresora.ubicacion."""
    ubicacion = UbicacionAgrupadaField(empty_label="-- Buscar nueva ubicación... --")

    class Meta:
        model = Impresora
        fields = ['ubicacion']
