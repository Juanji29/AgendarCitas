from django.core.exceptions import ValidationError

from .builders import CitaBuilder
from .factories import NotificadorFactory
from .models import Cita


class CitaService:
    """Capa de aplicación: orquesta el Builder (construye y valida) y la Factory (notifica)."""

    @staticmethod
    def agendar_cita(datos):
        cita = (
            CitaBuilder()
            .con_paciente(datos['paciente_nombre'], datos.get('paciente_email', ''))
            .con_medico(datos['medico_nombre'])
            .con_especialidad(datos['especialidad'])
            .con_fecha_hora(datos['fecha'], datos['hora'])
            .con_motivo(datos.get('motivo', ''))
            .build()
        )

        CitaService._validar_disponibilidad(cita)

        cita.save()

        notificador = NotificadorFactory.crear_notificador()
        notificador.notificar_confirmacion(cita)

        return cita

    @staticmethod
    def _validar_disponibilidad(cita):
        conflicto = Cita.objects.filter(
            medico_nombre=cita.medico_nombre,
            fecha=cita.fecha,
            hora=cita.hora,
        ).exclude(estado=Cita.ESTADO_CANCELADA).exists()

        if conflicto:
            raise ValidationError('El médico ya tiene una cita agendada en ese horario.')
