from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Paciente


class PatientRegistrationSerializer(serializers.Serializer):
    nombre = serializers.CharField(label=_('Nombre'), max_length=100)
    apellido = serializers.CharField(label=_('Apellido'), max_length=100)
    dni = serializers.CharField(label=_('Documento'), max_length=12)
    correo = serializers.EmailField(label=_('Correo electrónico'))
    telefono = serializers.CharField(label=_('Teléfono'), max_length=13)
    password = serializers.CharField(
        label=_('Contraseña'),
        write_only=True,
        trim_whitespace=False,
    )
    password2 = serializers.CharField(
        label=_('Confirmar contraseña'),
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password2': _('Las contraseñas no coinciden.')}
            )
        return attrs


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ('id', 'nombre', 'apellido', 'dni', 'correo', 'telefono')
        read_only_fields = fields
        extra_kwargs = {
            'id': {'label': _('ID')},
            'nombre': {'label': _('Nombre')},
            'apellido': {'label': _('Apellido')},
            'dni': {'label': _('Documento')},
            'correo': {'label': _('Correo electrónico')},
            'telefono': {'label': _('Teléfono')},
        }


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(label=_('ID'), read_only=True)
    username = serializers.CharField(label=_('Nombre de usuario'), read_only=True)
    email = serializers.EmailField(label=_('Correo electrónico'), read_only=True)
    first_name = serializers.CharField(label=_('Nombre'), read_only=True)
    last_name = serializers.CharField(label=_('Apellido'), read_only=True)
