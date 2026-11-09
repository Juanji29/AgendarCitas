from rest_framework import serializers

from .models import Paciente


class PatientRegistrationSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    apellido = serializers.CharField(max_length=100)
    dni = serializers.CharField(max_length=12)
    correo = serializers.EmailField()
    telefono = serializers.CharField(max_length=13)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password2': 'Las contraseñas no coinciden.'}
            )
        return attrs


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ('id', 'nombre', 'apellido', 'dni', 'correo', 'telefono')
        read_only_fields = fields


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
