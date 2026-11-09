from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Cita, Especialidad
from usuarios.models import Medico


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = (
            'id',
            'nombre',
            'duracion_minutos',
            'requiere_referido',
            'activa',
        )
        read_only_fields = fields
        extra_kwargs = {
            'id': {'label': _('ID')},
            'nombre': {'label': _('Nombre')},
            'duracion_minutos': {'label': _('Duración en minutos')},
            'requiere_referido': {'label': _('Requiere referido')},
            'activa': {'label': _('Activa')},
        }


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medico
        fields = ('id', 'nombre', 'apellido')
        read_only_fields = fields
        extra_kwargs = {
            'id': {'label': _('ID')},
            'nombre': {'label': _('Nombre')},
            'apellido': {'label': _('Apellido')},
        }


class DoctorListQuerySerializer(serializers.Serializer):
    especialidad = serializers.IntegerField(
        label=_('Especialidad'),
        min_value=1,
    )


class AppointmentCreateSerializer(serializers.Serializer):
    paciente_nombre = serializers.CharField(
        label=_('Nombre del paciente'),
        max_length=150,
    )
    paciente_email = serializers.EmailField(
        label=_('Correo electrónico del paciente'),
        required=False,
        allow_blank=True,
    )
    medico_nombre = serializers.CharField(label=_('Médico'), max_length=150)
    especialidad = serializers.PrimaryKeyRelatedField(
        label=_('Especialidad'),
        queryset=Especialidad.objects.all(),
    )
    fecha = serializers.DateField(label=_('Fecha'))
    hora = serializers.TimeField(label=_('Hora'))
    motivo = serializers.CharField(label=_('Motivo'), required=False, allow_blank=True)


class AppointmentSerializer(serializers.ModelSerializer):
    especialidad = SpecialtySerializer(read_only=True)

    class Meta:
        model = Cita
        fields = (
            'id',
            'paciente_nombre',
            'paciente_email',
            'medico_nombre',
            'especialidad',
            'fecha',
            'hora',
            'motivo',
            'duracion_minutos',
            'requiere_referido',
            'estado',
            'creada_en',
        )
        read_only_fields = fields
        extra_kwargs = {
            'id': {'label': _('ID')},
            'paciente_nombre': {'label': _('Nombre del paciente')},
            'paciente_email': {'label': _('Correo electrónico del paciente')},
            'medico_nombre': {'label': _('Médico')},
            'fecha': {'label': _('Fecha')},
            'hora': {'label': _('Hora')},
            'motivo': {'label': _('Motivo')},
            'duracion_minutos': {'label': _('Duración en minutos')},
            'requiere_referido': {'label': _('Requiere referido')},
            'estado': {'label': _('Estado')},
            'creada_en': {'label': _('Creada en')},
        }
