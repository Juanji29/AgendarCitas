"""Inicializa la app Celery junto con Django.

El import es tolerante a fallos: si Celery no está instalado (p. ej. en el
entorno local de pruebas del monolito), el proyecto sigue funcionando sin
tareas asíncronas.
"""
try:
    from .celery import app as celery_app

    __all__ = ('celery_app',)
except ImportError:  # Celery no instalado en este entorno
    celery_app = None
    __all__ = ()
