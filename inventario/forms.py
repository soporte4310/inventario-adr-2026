from django import forms
from .models import Activo, Ubicacion, Catalogo


class UbicacionChoiceField(forms.ModelChoiceField):
    """
    Campo personalizado que formatea el texto de la opción.
    Enviamos el nombre de la ubicación y su contexto (edificio/piso)
    separados por un carácter especial (|) para que el Frontend lo procese.
    """
    def label_from_instance(self, obj):
        # Ejemplo de salida: "Pasillo Central|Edificio A - Piso 2"
        return f"{obj.nombre}|{obj.piso.edificio.nombre} - {obj.piso.nombre}"


class ActivoForm(forms.ModelForm):
    ubicacion = UbicacionChoiceField(
        queryset=Ubicacion.objects.select_related('piso__edificio').all(),
        widget=forms.Select(attrs={'class': 'form-control select2-ubicacion'}),
        required=False,
        empty_label="-- Buscar ubicación... --"
    )

    class Meta:
        model = Activo
        fields = [
            'catalogo', 'estado', 
            'numero_serie', 'etiqueta', 'bdo', 
            'tipo_red', 'netbios', 'tipo_uso', 
            'ubicacion', 'asignado_a'
        ]
        widgets = {
            'catalogo': forms.Select(attrs={'class': 'form-control select2'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            
            'numero_serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PF2X89A'}),
            'etiqueta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: ADR-001'}),
            'bdo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 11180 (Se autocompleta con 26)'}),
            
            'tipo_red': forms.Select(attrs={'class': 'form-control'}),
            'netbios': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: NB-IQQ-01'}),
            'tipo_uso': forms.Select(attrs={'class': 'form-control'}),
            
            'asignado_a': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos el kwarg personalizado antes de pasarlo al super()
        categoria_nombre = kwargs.pop('categoria_nombre', None)
        
        super().__init__(*args, **kwargs)
        
        # 1. Asignamos placeholders a los campos no obligatorios
        for field in self.fields.values():
            if not field.required:
                field.widget.attrs['placeholder'] = field.widget.attrs.get('placeholder', 'Opcional')

        # 2. Reglas de Negocio para el Catálogo
        if self.instance and self.instance.pk:
            # MODO EDICIÓN: Bloquear catálogo
            self.fields['catalogo'].disabled = True
            self.fields['catalogo'].help_text = "🔒 El producto base no puede modificarse una vez registrado en el sistema."
        elif categoria_nombre:
            # MODO CREACIÓN FILTRADA: Limitar las opciones a la categoría solicitada
            qs_filtrado = Catalogo.objects.filter(categoria__nombre__iexact=categoria_nombre)
            self.fields['catalogo'].queryset = qs_filtrado
            self.fields['catalogo'].empty_label = f"-- Seleccione un modelo de {categoria_nombre} --"
            self.fields['catalogo'].help_text = f"💡 Mostrando únicamente productos de la categoría '{categoria_nombre}'."