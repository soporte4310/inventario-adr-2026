from django import forms
from .models import Activo, Ubicacion, Catalogo, Categoria
from common.mixins import ImageProcessingFormMixin


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




class CatalogoForm(ImageProcessingFormMixin, forms.ModelForm):
    class Meta:
        model = Catalogo
        fields = ['categoria', 'marca', 'modelo', 'descripcion', 'imagen']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select select2'}),
            'marca': forms.Select(attrs={'class': 'form-select select2'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: LATITUDE 5420 o GENÉRICO'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalles adicionales (opcional)'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def save(self, commit=True):
        # 1. Obtenemos la instancia sin guardar en BD todavía
        instance = super().save(commit=False)
        
        # 2. Verificamos si se subió una NUEVA imagen en este request
        # Esto evita procesar de nuevo si el usuario solo editó un texto
        if 'imagen' in self.changed_data and self.cleaned_data.get('imagen'):
            # 3. Ejecutamos el Mixin. Configuramos un tamaño prudente y forzamos un crop cuadrado (1:1)
            self.process_image_upload(
                instance=instance,
                field_name='imagen',
                max_dim=(1024, 1024),
                crop=True, 
                image_prefix='cat'
            )
            
        if commit:
            instance.save()
            
        return instance




class CategoriaForm(ImageProcessingFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'usa_netbios', 'usa_bdo', 'imagen']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: LAPTOPS, MONITORES, etc.'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Breve descripción de la categoría...'}),
            'usa_netbios': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usa_bdo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Si se subió una imagen nueva, procesamos los thumbnails
        if 'imagen' in self.changed_data and self.cleaned_data.get('imagen'):
            self.process_image_upload(
                instance=instance,
                field_name='imagen',
                max_dim=(1024, 1024), # Tamaño máximo para la imagen principal
                crop=True,            # Forzamos proporción cuadrada para las tarjetas
                image_prefix='cat'    # Prefijo para el nombre del archivo
            )
            
        if commit:
            instance.save()
        return instance