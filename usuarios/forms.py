from django import forms
from django.contrib.auth.models import Group

class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']
        labels = {
            'name': 'Nombre del Rol / Grupo',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control border-start-0',
                'placeholder': 'Ej: Supervisor ADR, Alumno en Práctica, Auditor...',
                'style': 'font-size: 0.9rem;'
            }),
        }


class GroupUpdateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']
        labels = {
            'name': 'Nombre del Rol / Grupo',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control border-start-0',
                'placeholder': 'Ej: Operador ADR...',
                'style': 'font-size: 0.9rem;'
            }),
        }