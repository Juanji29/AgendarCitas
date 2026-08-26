from django.db import models

class Persona(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(max_length=12)
    correo = models.EmailField()
    telefono = models.CharField(max_length=13)

    def __str__(self):
        return f'{self.nombre} {self.apellido}'

    class Meta:
        abstract = True

class Paciente(Persona):
    pass


class Medico(Persona):
    registro_medico = models.CharField(max_length=100)


