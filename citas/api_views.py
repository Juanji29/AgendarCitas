from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import gettext_lazy as _

from usuarios.serializers import PatientRegistrationSerializer, UserSerializer
from usuarios.services import UsuarioService

from .exceptions import ConflictError, DomainValidationError, NotFoundError
from .serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    DoctorListQuerySerializer,
    DoctorSerializer,
    SpecialtySerializer,
)
from .services import CitaService


def _error_response(code, detail, http_status):
    return Response(
        {'error': code, 'detail': detail},
        status=http_status,
    )


class SpecialtyListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        specialties = CitaService.obtener_especialidades()
        return Response({'data': SpecialtySerializer(specialties, many=True).data})


class DoctorListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query_serializer = DoctorListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return _error_response(
                'validation_error',
                query_serializer.errors,
                status.HTTP_400_BAD_REQUEST,
            )

        doctors = CitaService.obtener_medicos(
            query_serializer.validated_data['especialidad'],
        )
        return Response({'data': DoctorSerializer(doctors, many=True).data})


class AppointmentListCreateAPIView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        appointments = CitaService.obtener_citas_paciente(request.user.email)
        return Response({'data': AppointmentSerializer(appointments, many=True).data})

    def post(self, request):
        input_serializer = AppointmentCreateSerializer(data=request.data)
        if not input_serializer.is_valid():
            return _error_response(
                'validation_error',
                input_serializer.errors,
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            appointment = CitaService.agendar_cita(input_serializer.validated_data)
        except DomainValidationError as error:
            return _error_response(
                'validation_error',
                str(error),
                status.HTTP_400_BAD_REQUEST,
            )
        except ConflictError as error:
            return _error_response(
                'conflict',
                str(error),
                status.HTTP_409_CONFLICT,
            )

        return Response(
            {'data': AppointmentSerializer(appointment).data},
            status=status.HTTP_201_CREATED,
        )


class AppointmentCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, appointment_id):
        try:
            appointment = CitaService.cancelar_cita(
                appointment_id,
                request.user.email,
            )
        except NotFoundError as error:
            return _error_response(
                'not_found',
                str(error),
                status.HTTP_404_NOT_FOUND,
            )
        except ConflictError as error:
            return _error_response(
                'conflict',
                str(error),
                status.HTTP_409_CONFLICT,
            )

        return Response({'data': AppointmentSerializer(appointment).data})


class PatientRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        input_serializer = PatientRegistrationSerializer(data=request.data)
        if not input_serializer.is_valid():
            return _error_response(
                'validation_error',
                input_serializer.errors,
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = UsuarioService.registrar_paciente(input_serializer.validated_data)
        except IntegrityError:
            return _error_response(
                'conflict',
                _('Ya existe una cuenta con esos datos.'),
                status.HTTP_409_CONFLICT,
            )

        return Response(
            {'data': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class AppointmentSummaryAPIView(APIView):
    """Servicio a Proveer: endpoint JSON con información agregada del sistema.

    Expone conteos de citas (total, por especialidad y por estado) sin datos
    personales. Es el servicio que el equipo aliado puede consumir.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        resumen = CitaService.generar_resumen()
        resumen['generado_en'] = timezone.now().isoformat()
        return Response({'data': resumen})


class SystemInfoAPIView(APIView):
    """Servicio a Proveer: metadatos del sistema para el equipo aliado.

    Devuelve identidad y capacidades del servicio para facilitar la
    integración entre equipos (descubrimiento del contrato).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'data': {
                'servicio': 'healthbook-citas',
                'descripcion': str(_('Agenda de citas médicas HealthBook.')),
                'version': 'v1',
                'idiomas': [codigo for codigo, _nombre in settings.LANGUAGES],
                'endpoints': {
                    'resumen': '/api/v1/citas/resumen/',
                    'especialidades': '/api/v1/especialidades/',
                    'medicos': '/api/v1/medicos/',
                    'citas': '/api/v1/citas/',
                },
                'generado_en': timezone.now().isoformat(),
            }
        })


class AllyServiceAPIView(APIView):
    """Servicio a Consumir: muestra en nuestra app el resumen del equipo aliado.

    Consume el servicio del aliado mediante el Patrón Adapter (puerto
    ServicioAliadoPort). Si el aliado no responde, devuelve disponible=False
    sin propagar el fallo (resiliencia).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        resumen = CitaService.consumir_resumen_aliado()
        return Response({
            'data': {
                'servicio': resumen.servicio,
                'disponible': resumen.disponible,
                'total': resumen.total,
                'detalle': resumen.detalle,
            }
        })
