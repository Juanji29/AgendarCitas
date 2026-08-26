from django.test import TestCase
from django.contrib.auth import get_user_model

from usuarios.models import Paciente
from usuarios.models import Medico


class AgendarCitaViewTests(TestCase):
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
		usuario = get_user_model().objects.create_user(
			username='ana@example.com',
			email='ana@example.com',
			password='UnaClaveSegura123!',
		)
		Paciente.objects.create(
			nombre='Ana',
			apellido='Gomez',
			dni='123456789',
			correo='ana@example.com',
			telefono='3001234567',
		)
		self.client.force_login(usuario)

		response = self.client.get('/citas/agendar/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['form']['paciente_nombre'].value(), 'Ana Gomez')
		self.assertEqual(response.context['form']['paciente_email'].value(), 'ana@example.com')

	def test_get_does_not_prefill_anonymous_patient_data(self):
		response = self.client.get('/citas/agendar/')

		self.assertEqual(response.status_code, 200)
		self.assertIsNone(response.context['form']['paciente_nombre'].value())
		self.assertIsNone(response.context['form']['paciente_email'].value())
