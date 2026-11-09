from django.core.exceptions import ValidationError
from django.db.models import Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .builders import CitaBuilder
from .exceptions import ConflictError, DomainValidationError, NotFoundError
from .factories import NotificadorFactory
from .models import Cita, Especialidad
from usuarios.models import Medico


class CitaService:
    """Capa de aplicación: orquesta el Builder (construye y valida) y la Factory (notifica)."""

    @staticmethod
    def agendar_cita(datos):
        try:
            cita = (
                CitaBuilder()
                .con_paciente(datos['paciente_nombre'], datos.get('paciente_email', ''))
                .con_medico(datos['medico_nombre'])
                .con_especialidad(datos['especialidad'])
                .con_fecha_hora(datos['fecha'], datos['hora'])
                .con_motivo(datos.get('motivo', ''))
                .build()
            )
        except ValidationError as error:
            raise DomainValidationError(str(error)) from error

        CitaService._validar_fecha(cita)

        if not Medico.objects.annotate(
            nombre_completo=Concat('nombre', Value(' '), 'apellido'),
        ).filter(
            nombre_completo=datos['medico_nombre'],
            especialidades=datos['especialidad'],
        ).exists():
            raise DomainValidationError(
                _('El médico seleccionado no está asociado a esta especialidad.')
            )

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
    def obtener_especialidades():
        return Especialidad.objects.filter(activa=True)

    @staticmethod
    def obtener_medicos(especialidad_id):
        return Medico.objects.filter(
            especialidades__id=especialidad_id,
        ).order_by('apellido', 'nombre').distinct()

    @staticmethod
    def cancelar_cita(cita_id, correo):
        try:
            cita = Cita.objects.get(
                id=cita_id,
                paciente_email=correo,
            )
        except Cita.DoesNotExist as error:
            raise NotFoundError(
                _('La cita no existe o no pertenece al paciente.')
            ) from error

        if cita.estado == Cita.ESTADO_CANCELADA:
            raise ConflictError(_('La cita ya está cancelada.'))

        cita.estado = Cita.ESTADO_CANCELADA
        cita.save(update_fields=['estado'])
        return cita

    @staticmethod
    def _validar_fecha(cita):
        if cita.fecha < timezone.localdate():
            raise DomainValidationError(
                _('No se pueden agendar citas en fechas pasadas.')
            )

    @staticmethod
    def _validar_disponibilidad(cita):
        conflicto = Cita.objects.filter(
            medico_nombre=cita.medico_nombre,
            fecha=cita.fecha,
            hora=cita.hora,
        ).exclude(estado=Cita.ESTADO_CANCELADA).exists()

        if conflicto:
            raise ConflictError(
                _('El médico ya tiene una cita agendada en ese horario.')
            )
