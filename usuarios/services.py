from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Paciente


class UsuarioService:
    @staticmethod
    @transaction.atomic
    def registrar_paciente(datos):
        usuario = get_user_model().objects.create_user(
            username=datos['correo'],
            email=datos['correo'],
            password=datos['password'],
            first_name=datos['nombre'],
            last_name=datos['apellido'],
        )
        Paciente.objects.create(
            nombre=datos['nombre'],
            apellido=datos['apellido'],
            dni=datos['dni'],
            correo=datos['correo'],
            telefono=datos['telefono'],
        )
        return usuario