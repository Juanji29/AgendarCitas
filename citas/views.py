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
        citas = CitaService.obtener_citas_paciente(request.user.email) if request.user.is_authenticated else []
        return render(request, self.template_name, {'form': form, 'citas': citas})

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


def cancelar_cita(request, cita_id):
    if request.method != 'POST' or not request.user.is_authenticated:
        return redirect('usuarios:login')

    try:
        CitaService.cancelar_cita(cita_id, request.user.email)
    except ValidationError:
        pass

    return redirect('citas:agendar_cita')
