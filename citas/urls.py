from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'citas'

urlpatterns = [
    path('agendar/', views.AgendarCitaView.as_view(), name='agendar_cita'),
    path(
        'agendar/confirmacion/',
        TemplateView.as_view(template_name='citas/cita_agendada.html'),
        name='cita_agendada',
    ),
]
