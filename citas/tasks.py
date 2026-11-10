"""Tareas asíncronas (Message Broker: Redis + Celery).

Procesos de fondo que no deben bloquear el ciclo request/response:
  - enviar_notificacion_confirmacion: delega la notificación de una cita.
  - generar_reporte_resumen: calcula el resumen agregado del sistema.

El import de Celery es tolerante a fallos: si Celery no está instalado, se
define un decorador ``shared_task`` de reemplazo que ejecuta la función de
forma síncrona, de modo que el monolito sigue operando sin broker.
"""
import logging

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:  # pragma: no cover - entorno sin Celery
    def shared_task(*dargs, **dkwargs):
        def _decorador(func):
            def _wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            # Emula la API de Celery usada en el código.
            _wrapper.delay = lambda *a, **k: func(*a, **k)
            _wrapper.run = func
            return _wrapper

        # Permite usar @shared_task y @shared_task(bind=False) indistintamente.
        if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
            return _decorador(dargs[0])
        return _decorador


@shared_task(name='citas.enviar_notificacion_confirmacion')
def enviar_notificacion_confirmacion(cita_id):
    """Envía la notificación de confirmación de una cita en segundo plano."""
    from .models import Cita
    from .factories import NotificadorFactory

    try:
        cita = Cita.objects.select_related('especialidad').get(id=cita_id)
    except Cita.DoesNotExist:
        logger.warning('Cita %s no existe; no se notifica.', cita_id)
        return {'cita_id': cita_id, 'enviado': False, 'motivo': 'no_existe'}

    NotificadorFactory.crear_notificador().notificar_confirmacion(cita)
    return {'cita_id': cita_id, 'enviado': True}


@shared_task(name='citas.generar_reporte_resumen')
def generar_reporte_resumen():
    """Genera el resumen agregado del sistema como tarea de fondo."""
    from .services import CitaService

    return CitaService.generar_resumen()
