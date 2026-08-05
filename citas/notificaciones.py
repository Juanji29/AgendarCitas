from abc import ABC, abstractmethod

from django.core.mail import send_mail


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
