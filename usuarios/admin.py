from django.contrib import admin

from .models import Medico, Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'apellido', 'dni', 'correo', 'telefono')
	search_fields = ('nombre', 'apellido', 'dni', 'correo')


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'apellido', 'dni', 'correo', 'telefono', 'registro_medico')
	search_fields = ('nombre', 'apellido', 'dni', 'correo', 'registro_medico')
