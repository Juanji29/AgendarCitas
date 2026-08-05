from .models import Cita

_POLITICAS_ESPECIALIDAD = {
    'cardiologia': {'duracion_minutos': 30, 'requiere_referido': True},
    'pediatria': {'duracion_minutos': 25, 'requiere_referido': False},
    'dermatologia': {'duracion_minutos': 20, 'requiere_referido': False},
    'medicina general': {'duracion_minutos': 20, 'requiere_referido': False},
}
_POLITICA_POR_DEFECTO = {'duracion_minutos': 20, 'requiere_referido': False}


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
        politica = _POLITICAS_ESPECIALIDAD.get(
            (especialidad or '').strip().lower(), _POLITICA_POR_DEFECTO
        )
        self._cita.duracion_minutos = politica['duracion_minutos']
        self._cita.requiere_referido = politica['requiere_referido']
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
