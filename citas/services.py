from django.core.exceptions import ValidationError
from django.db.models import Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .builders import CitaBuilder
from .exceptions import ConflictError, DomainValidationError, NotFoundError
from .factories import IntegracionesFactory, NotificadorFactory
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

        # Message Broker (Celery): la notificación se procesa en segundo plano
        # para no bloquear el agendamiento. Si Celery no está disponible, la
        # tarea de reemplazo la ejecuta de forma síncrona (resiliencia).
        from .tasks import enviar_notificacion_confirmacion
        enviar_notificacion_confirmacion.delay(cita.id)

        return cita

    @staticmethod
    def obtener_citas_paciente(correo):
        return Cita.objects.filter(
            paciente_email=correo,
        ).exclude(
            estado=Cita.ESTADO_CANCELADA,
        ).select_related('especialidad').order_by('fecha', 'hora')

    @staticmethod
    def generar_resumen():
        """Agrega conteos de citas sin exponer datos personales (PII).

        Devuelve:
          - total: todas las citas, incluidas canceladas.
          - por_especialidad: conteo por especialidad local (id + nombre).
          - por_estado: conteo por cada estado definido en el modelo.
        """
        from django.db.models import Count

        total = Cita.objects.count()

        por_especialidad = list(
            Cita.objects.values('especialidad__id', 'especialidad__nombre')
            .annotate(total=Count('id'))
            .order_by('especialidad__id')
        )
        por_especialidad = [
            {
                'id': fila['especialidad__id'],
                'nombre': fila['especialidad__nombre'],
                'total': fila['total'],
            }
            for fila in por_especialidad
        ]

        conteos = dict(
            Cita.objects.values_list('estado').annotate(total=Count('id'))
        )
        por_estado = {
            estado: conteos.get(estado, 0)
            for estado, _etiqueta in Cita.ESTADO_CHOICES
        }

        return {
            'total': total,
            'por_especialidad': por_especialidad,
            'por_estado': por_estado,
        }

    @staticmethod
    def consultar_festivo(fecha, proveedor=None):
        """Consulta la API de terceros (vía Adapter) si la fecha es festiva.

        Depende del puerto ProveedorDiasFestivosPort, no de la API concreta.
        Nunca lanza: ante fallo externo, el adaptador degrada a no festivo.
        """
        proveedor = proveedor or IntegracionesFactory.proveedor_festivos()
        return proveedor.es_festivo(fecha)

    @staticmethod
    def consumir_resumen_aliado(servicio=None):
        """Consume el servicio del equipo aliado (vía Adapter).

        Depende del puerto ServicioAliadoPort. Devuelve un ResumenAliado
        normalizado, con disponible=False si el aliado no responde.
        """
        servicio = servicio or IntegracionesFactory.servicio_aliado()
        return servicio.obtener_resumen()

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
