from django import forms

from .models import Cita
from .services import CitaService
from usuarios.models import Medico


class CitaForm(forms.ModelForm):
    medico_nombre = forms.ModelChoiceField(
        queryset=Medico.objects.none(),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        especialidad_id = (
            self.data.get('especialidad')
            or self.initial.get('especialidad')
        )
        if especialidad_id:
            try:
                especialidad_id = int(especialidad_id)
            except (TypeError, ValueError):
                return
            self.fields['medico_nombre'].queryset = CitaService.obtener_medicos(
                especialidad_id,
            )

    def clean_medico_nombre(self):
        medico = self.cleaned_data['medico_nombre']
        return f'{medico.nombre} {medico.apellido}'
