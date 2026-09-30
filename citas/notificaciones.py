import logging
from abc import ABC, abstractmethod
from urllib import request as urllib_request
from urllib import error as urllib_error
import json

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class Notificador(ABC):
    @abstractmethod
    def notificar_confirmacion(self, cita):
        raise NotImplementedError


class EmailNotificador(Notificador):
    """Dependencia externa: envía la confirmación por correo electrónico."""

    def notificar_confirmacion(self, cita):
        if not cita.paciente_email:
            return
        send_mail(
            subject='Confirmación de cita médica',
            message=(
                f'Hola {cita.paciente_nombre}, tu cita con {cita.medico_nombre} '
                f'({cita.especialidad}) quedó agendada para el {cita.fecha} a las {cita.hora}.'
            ),
            from_email=None,
            recipient_list=[cita.paciente_email],
        )


class NotificadorConsola(Notificador):
    """Servicio de apoyo alterno: registra la notificación sin enviar correo."""

    def notificar_confirmacion(self, cita):
        print(f'[Notificación] Cita #{cita.id} confirmada para {cita.paciente_nombre}.')


class NotificadorHTTP(Notificador):
    """Cliente del microservicio de Notificaciones (Strangler Pattern).

    En lugar de enviar el correo dentro del monolito, delega la notificación
    al microservicio Flask vía HTTP (JSON). Si el servicio no responde, el
    fallo se registra pero NO interrumpe el agendamiento de la cita.
    """

    def __init__(self, base_url=None, timeout=None):
        self._base_url = (
            base_url or getattr(settings, 'NOTIFICACIONES_SERVICE_URL', 'http://localhost:5000')
        ).rstrip('/')
        self._timeout = timeout or getattr(settings, 'NOTIFICACIONES_SERVICE_TIMEOUT', 5)

    def notificar_confirmacion(self, cita):
        payload = {
            'paciente_nombre': cita.paciente_nombre,
            'paciente_email': cita.paciente_email or '',
            'medico_nombre': cita.medico_nombre,
            'especialidad': str(cita.especialidad),
            'fecha': str(cita.fecha),
            'hora': str(cita.hora),
        }
        url = f'{self._base_url}/api/v2/notificaciones/confirmacion'
        datos = json.dumps(payload).encode('utf-8')
        peticion = urllib_request.Request(
            url,
            data=datos,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib_request.urlopen(peticion, timeout=self._timeout) as respuesta:
                cuerpo = respuesta.read().decode('utf-8')
                logger.info('Notificación delegada al microservicio: %s', cuerpo)
        except (urllib_error.URLError, TimeoutError) as error:
            # Resiliencia: un fallo del microservicio no debe tumbar el agendamiento.
            logger.error('No se pudo contactar el microservicio de notificaciones: %s', error)
