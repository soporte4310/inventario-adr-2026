from django import forms
from .models import CicloRevision, RevisionSala
from inventario.models import Activo


class CerrarRevisionForm(forms.ModelForm):
    observaciones_cierre = forms.CharField(
        label="Motivo u Observaciones de Cierre",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Indica el motivo del cierre (ej: Receso académico, salas pendientes por remodelación, etc.)",
            }
        ),
        help_text="Opcional. Quedará registrado en la auditoría del ciclo.",
    )

    class Meta:
        model = CicloRevision
        fields = ["observaciones_cierre"]




class RevisionSalaForm(forms.ModelForm):
    class Meta:
        model = RevisionSala
        fields = [
            'proyector',
            'proyector_encendido',
            'horas_lampara',
            'red_proyector_conectada',
            'proyeccion_inalambrica',
            'candado_proyector',
            'copla_hdmi',
            'panel_control',
            'puerto_red_pared',
            'audio_sala',
            'observaciones',
        ]
        widgets = {
            # Lo definimos como input oculto para que viaje dentro del POST de forma transparente
            'proyector': forms.HiddenInput(),
            'horas_lampara': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Ej: 1450',
                'min': '0'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detalla cualquier elemento marcado en Amarillo o Rojo (ej: Copla HDMI suelta, proyector proyecta con tono amarillo)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. El proyector es opcional en el formulario (permite salas que no tienen equipo)
        self.fields['proyector'].required = False
        self.fields['proyector'].queryset = Activo.objects.filter(
            catalogo__categoria__nombre__icontains="proyect",
            is_deleted=False
        )

        # 2. Infraestructura fija de sala: SIEMPRE obligatoria
        campos_sala = [
            'copla_hdmi',
            'panel_control',
            'puerto_red_pared',
            'audio_sala',
        ]
        for campo in campos_sala:
            if campo in self.fields:
                self.fields[campo].required = True
                self.fields[campo].error_messages = {
                    'required': 'Debes evaluar este elemento antes de guardar la revisión.'
                }

        # 3. Detectar si en esta petición hay proyector asignado
        tiene_proyector = False
        if self.data:
            # Viene de un POST: verificamos si 'proyector' trae un ID numérico válido
            val = self.data.get('proyector')
            tiene_proyector = bool(val and str(val).isdigit())
        elif self.instance and self.instance.proyector_id:
            # Viene de un GET inicial: la sala ya tiene proyector en BD
            tiene_proyector = True

        # 4. Semáforos de proyector: SOLO obligatorios si hay proyector presente
        campos_proyector = [
            'proyector_encendido',
            'red_proyector_conectada',
            'proyeccion_inalambrica',
            'candado_proyector',
        ]
        for campo in campos_proyector:
            if campo in self.fields:
                self.fields[campo].required = tiene_proyector
                self.fields[campo].error_messages = {
                    'required': 'Debes evaluar este aspecto del proyector.'
                }