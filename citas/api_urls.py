from django.urls import path

from .api_views import (
    AppointmentCancelAPIView,
    AppointmentListCreateAPIView,
    PatientRegistrationAPIView,
    SpecialtyListAPIView,
)

app_name = 'api_v1'

urlpatterns = [
    path('especialidades/', SpecialtyListAPIView.as_view(), name='especialidades'),
    path('citas/', AppointmentListCreateAPIView.as_view(), name='citas'),
    path(
        'citas/<int:appointment_id>/cancelar/',
        AppointmentCancelAPIView.as_view(),
        name='cancelar_cita',
    ),
    path('usuarios/registro/', PatientRegistrationAPIView.as_view(), name='registro'),
]
