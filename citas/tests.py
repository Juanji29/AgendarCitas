from datetime import date, time, timedelta
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model

from .services import CitaService
from .models import Cita, Especialidad
from usuarios.models import Paciente
from usuarios.models import Medico


class AgendarCitaViewTests(TestCase):
	def setUp(self):
		self.usuario = get_user_model().objects.create_user(
			username='ana@example.com',
			email='ana@example.com',
			password='UnaClaveSegura123!',
		)
		self.paciente = Paciente.objects.create(
			nombre='Ana',
			apellido='Gomez',
			dni='123456789',
			correo='ana@example.com',
			telefono='3001234567',
		)

	def test_get_muestra_medicos_de_la_base_de_datos(self):
		Medico.objects.create(
			nombre='Carlos',
			apellido='Perez',
			dni='987654321',
			correo='carlos@example.com',
			telefono='3009876543',
			registro_medico='RM-001',
		)

		response = self.client.get('/citas/agendar/')

		self.assertContains(response, 'Carlos Perez')
		self.assertContains(response, 'Seleccione un médico')

	def test_get_prefills_authenticated_patient_data(self):
		self.client.force_login(self.usuario)

		response = self.client.get('/citas/agendar/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['form']['paciente_nombre'].value(), 'Ana Gomez')
		self.assertEqual(response.context['form']['paciente_email'].value(), 'ana@example.com')

	def test_get_muestra_solo_las_citas_del_paciente_autenticado(self):
		especialidad = Especialidad.objects.create(nombre='Cardiologia', duracion_minutos=30)
		Cita.objects.create(
			paciente_nombre='Ana Gomez', paciente_email='ana@example.com',
			medico_nombre='Carlos Perez', especialidad=especialidad,
			fecha=date.today(), hora=time(10, 0),
		)
		Cita.objects.create(
			paciente_nombre='Otra Persona', paciente_email='otra@example.com',
			medico_nombre='Carlos Perez', especialidad=especialidad,
			fecha=date.today(), hora=time(11, 0),
		)
		self.client.force_login(self.usuario)

		response = self.client.get('/citas/agendar/')

		self.assertEqual(list(response.context['citas']), list(Cita.objects.filter(paciente_email='ana@example.com')))

	def test_paciente_puede_cancelar_su_cita(self):
		especialidad = Especialidad.objects.create(nombre='Cardiologia', duracion_minutos=30)
		cita = Cita.objects.create(
			paciente_nombre='Ana Gomez', paciente_email='ana@example.com',
			medico_nombre='Carlos Perez', especialidad=especialidad,
			fecha=date.today(), hora=time(10, 0),
		)
		self.client.force_login(self.usuario)

		response = self.client.post(f'/citas/agendar/cancelar/{cita.id}/')

		self.assertRedirects(response, '/citas/agendar/')
		cita.refresh_from_db()
		self.assertEqual(cita.estado, Cita.ESTADO_CANCELADA)


class CitaServiceTests(TestCase):
	@patch('citas.notificaciones.urllib_request.urlopen')
	def test_notificador_http_envia_la_notificacion_por_nginx(self, urlopen):
		respuesta = Mock()
		respuesta.read.return_value = b'{"enviado": true}'
		respuesta.__enter__ = Mock(return_value=respuesta)
		respuesta.__exit__ = Mock(return_value=False)
		urlopen.return_value = respuesta
		cita = SimpleNamespace(
			paciente_nombre='Ana Gomez',
			paciente_email='ana@example.com',
			medico_nombre='Carlos Perez',
			especialidad='Cardiologia',
			fecha=date(2026, 10, 1),
			hora=time(10, 0),
		)

		from .notificaciones import NotificadorHTTP
		NotificadorHTTP(base_url='http://nginx').notificar_confirmacion(cita)

		peticion = urlopen.call_args.args[0]
		self.assertEqual(
			peticion.full_url,
			'http://nginx/api/v2/notificaciones/confirmacion',
		)
		self.assertEqual(peticion.get_method(), 'POST')
		self.assertEqual(json.loads(peticion.data), {
			'paciente_nombre': 'Ana Gomez',
			'paciente_email': 'ana@example.com',
			'medico_nombre': 'Carlos Perez',
			'especialidad': 'Cardiologia',
			'fecha': '2026-10-01',
			'hora': '10:00:00',
		})

	def test_no_permite_agendar_citas_en_fecha_pasada(self):
		especialidad = Especialidad.objects.create(
			nombre='Cardiologia',
			duracion_minutos=30,
			requiere_referido=True,
		)

		with self.assertRaisesMessage(
			ValidationError,
			'No se pueden agendar citas en fechas pasadas.',
		):
			CitaService.agendar_cita({
				'paciente_nombre': 'Ana Gomez',
				'paciente_email': 'ana@example.com',
				'medico_nombre': 'Carlos Perez',
				'especialidad': especialidad,
				'fecha': date.today() - timedelta(days=1),
				'hora': time(10, 0),
				'motivo': 'Consulta',
			})

	def test_get_does_not_prefill_anonymous_patient_data(self):
		response = self.client.get('/citas/agendar/')

		self.assertEqual(response.status_code, 200)
		self.assertIsNone(response.context['form']['paciente_nombre'].value())
		self.assertIsNone(response.context['form']['paciente_email'].value())
