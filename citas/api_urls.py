from django.urls import path

from .api_views import (
    AllyServiceAPIView,
    AppointmentCancelAPIView,
    AppointmentListCreateAPIView,
    AppointmentSummaryAPIView,
    DoctorListAPIView,
    PatientRegistrationAPIView,
    SpecialtyListAPIView,
    SystemInfoAPIView,
)

app_name = 'api_v1'

urlpatterns = [
    path('especialidades/', SpecialtyListAPIView.as_view(), name='especialidades'),
    path('medicos/', DoctorListAPIView.as_view(), name='medicos'),
    path('citas/resumen/', AppointmentSummaryAPIView.as_view(), name='resumen'),
    path('citas/', AppointmentListCreateAPIView.as_view(), name='citas'),
    path(
        'citas/<int:appointment_id>/cancelar/',
        AppointmentCancelAPIView.as_view(),
        name='cancelar_cita',
    ),
    path('usuarios/registro/', PatientRegistrationAPIView.as_view(), name='registro'),
    path('info/', SystemInfoAPIView.as_view(), name='info'),
    path('aliado/resumen/', AllyServiceAPIView.as_view(), name='aliado'),
]
