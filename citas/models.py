from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    duracion_minutos = models.PositiveSmallIntegerField()
    requiere_referido = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Especialidades'

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_CONFIRMADA = 'confirmada'
    ESTADO_CANCELADA = 'cancelada'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    paciente_nombre = models.CharField(max_length=150)
    paciente_email = models.EmailField(blank=True)
    medico_nombre = models.CharField(max_length=150)
    especialidad = models.ForeignKey(
        Especialidad, null=False, on_delete=models.PROTECT
    )
    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.TextField(blank=True)
    duracion_minutos = models.PositiveSmallIntegerField(default=20)
    requiere_referido = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.paciente_nombre} con {self.medico_nombre} el {self.fecha} {self.hora}'

    def clean(self):
        if self.fecha and self.fecha < timezone.localdate():
            raise ValidationError({'fecha': 'No se pueden agendar citas en fechas pasadas.'})
