from rest_framework import serializers

from .models import Cita, Especialidad


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


class AppointmentCreateSerializer(serializers.Serializer):
    paciente_nombre = serializers.CharField(max_length=150)
    paciente_email = serializers.EmailField(required=False, allow_blank=True)
    medico_nombre = serializers.CharField(max_length=150)
    especialidad = serializers.PrimaryKeyRelatedField(
        queryset=Especialidad.objects.all()
    )
    fecha = serializers.DateField()
    hora = serializers.TimeField()
    motivo = serializers.CharField(required=False, allow_blank=True)


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
