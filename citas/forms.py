from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Cita
from .services import CitaService
from usuarios.models import Medico


class CitaForm(forms.ModelForm):
    medico_nombre = forms.ModelChoiceField(
        queryset=Medico.objects.none(),
        label=_('Médico'),
        empty_label=_('Seleccione un médico'),
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
        labels = {
            'paciente_nombre': _('Nombre del paciente'),
            'paciente_email': _('Correo electrónico del paciente'),
            'especialidad': _('Especialidad'),
            'fecha': _('Fecha'),
            'hora': _('Hora'),
            'motivo': _('Motivo'),
        }
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
