from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import View

from .forms import CitaForm
from .services import CitaService


class AgendarCitaView(View):
    template_name = 'citas/agendar_cita.html'

    def get(self, request):
        form = CitaForm()
        return render(request, self.template_name, {'form': form})

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
