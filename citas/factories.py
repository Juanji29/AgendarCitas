from django.conf import settings

from .notificaciones import EmailNotificador, NotificadorConsola


class NotificadorFactory:
    """Factory: instancia el servicio de apoyo externo encargado de notificar al paciente."""

    @staticmethod
    def crear_notificador():
        if getattr(settings, 'NOTIFICAR_POR_EMAIL', True):
            return EmailNotificador()
        return NotificadorConsola()
