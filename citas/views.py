from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import View

from .forms import CitaForm
from usuarios.models import Paciente
from .services import CitaService


class AgendarCitaView(View):
    template_name = 'citas/agendar_cita.html'

    def get(self, request):
        form = CitaForm(initial=self._datos_paciente(request))
        return render(request, self.template_name, {'form': form})

    @staticmethod
    def _datos_paciente(request):
        if not request.user.is_authenticated:
            return {}

        paciente = Paciente.objects.filter(correo=request.user.email).first()
        if paciente is None:
            return {}

        return {
            'paciente_nombre': f'{paciente.nombre} {paciente.apellido}',
            'paciente_email': paciente.correo,
        }

    def post(self, request):
        form = CitaForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        try:
            CitaService.agendar_cita(form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
            return render(request, self.template_name, {'form': form})

        return redirect('citas:cita_agendada')
