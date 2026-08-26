from django.core.exceptions import ValidationError
from django.utils import timezone

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

        CitaService._validar_fecha(cita)
        CitaService._validar_disponibilidad(cita)

        cita.save()

        notificador = NotificadorFactory.crear_notificador()
        notificador.notificar_confirmacion(cita)

        return cita

    @staticmethod
    def obtener_citas_paciente(correo):
        return Cita.objects.filter(
            paciente_email=correo,
        ).exclude(
            estado=Cita.ESTADO_CANCELADA,
        ).select_related('especialidad').order_by('fecha', 'hora')

    @staticmethod
    def cancelar_cita(cita_id, correo):
        try:
            cita = Cita.objects.get(
                id=cita_id,
                paciente_email=correo,
            )
        except Cita.DoesNotExist as error:
            raise ValidationError('La cita no existe o no pertenece al paciente.') from error

        if cita.estado == Cita.ESTADO_CANCELADA:
            raise ValidationError('La cita ya está cancelada.')

        cita.estado = Cita.ESTADO_CANCELADA
        cita.save(update_fields=['estado'])
        return cita

    @staticmethod
    def _validar_fecha(cita):
        if cita.fecha < timezone.localdate():
            raise ValidationError('No se pueden agendar citas en fechas pasadas.')

    @staticmethod
    def _validar_disponibilidad(cita):
        conflicto = Cita.objects.filter(
            medico_nombre=cita.medico_nombre,
            fecha=cita.fecha,
            hora=cita.hora,
        ).exclude(estado=Cita.ESTADO_CANCELADA).exists()

        if conflicto:
            raise ValidationError('El médico ya tiene una cita agendada en ese horario.')
