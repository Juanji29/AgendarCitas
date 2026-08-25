from .models import Cita


class CitaBuilder:
    """Construye una Cita paso a paso y garantiza que sea válida antes de guardarla."""

    def __init__(self):
        self._cita = Cita()

    def con_paciente(self, nombre, email=''):
        self._cita.paciente_nombre = nombre
        self._cita.paciente_email = email or ''
        return self

    def con_medico(self, nombre):
        self._cita.medico_nombre = nombre
        return self

    def con_especialidad(self, especialidad):
        self._cita.especialidad = especialidad
        self._cita.duracion_minutos = especialidad.duracion_minutos
        self._cita.requiere_referido = especialidad.requiere_referido
        return self

    def con_fecha_hora(self, fecha, hora):
        self._cita.fecha = fecha
        self._cita.hora = hora
        return self

    def con_motivo(self, motivo):
        self._cita.motivo = motivo or ''
        return self

    def build(self):
        self._cita.full_clean()
        return self._cita
