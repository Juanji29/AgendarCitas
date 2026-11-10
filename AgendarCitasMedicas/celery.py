"""Configuración de Celery para tareas de fondo (Message Broker).

Celery usa Redis como broker y backend de resultados. Las tareas pesadas o
dependientes de servicios externos (notificaciones, reportes) se ejecutan de
forma asíncrona fuera del ciclo request/response.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgendarCitasMedicas.settings')

app = Celery('AgendarCitasMedicas')

# Toma la configuración desde settings.py (claves con prefijo CELERY_).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubre tareas en cada app instalada (p. ej. citas/tasks.py).
app.autodiscover_tasks()
