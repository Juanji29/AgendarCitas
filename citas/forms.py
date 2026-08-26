from django import forms

from .models import Cita
from usuarios.models import Medico


class CitaForm(forms.ModelForm):
    medico_nombre = forms.ModelChoiceField(
        queryset=Medico.objects.all(),
        label='Médico',
        empty_label='Seleccione un médico',
    )

    class Meta:
        model = Cita
        fields = [
            'paciente_nombre',
            'paciente_email',
            'medico_nombre',
            'especialidad',
            'fecha',
            'hora',
            'motivo',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_medico_nombre(self):
        medico = self.cleaned_data['medico_nombre']
        return f'{medico.nombre} {medico.apellido}'
