from django.conf import settings

from .notificaciones import EmailNotificador, NotificadorConsola, NotificadorHTTP


class NotificadorFactory:
    """Factory: instancia el servicio de apoyo externo encargado de notificar al paciente.

    Estrategia (Strangler Pattern):
      - USAR_MICROSERVICIO_NOTIFICACIONES=True -> delega al microservicio Flask (NotificadorHTTP).
      - En caso contrario, se mantiene la lógica legacy dentro del monolito
        (EmailNotificador o NotificadorConsola según NOTIFICAR_POR_EMAIL).
    """

    @staticmethod
    def crear_notificador():
        if getattr(settings, 'USAR_MICROSERVICIO_NOTIFICACIONES', False):
            return NotificadorHTTP()

        if getattr(settings, 'NOTIFICAR_POR_EMAIL', True):
            return EmailNotificador()
        return NotificadorConsola()
