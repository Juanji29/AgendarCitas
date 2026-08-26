from django.test import TestCase

from django.contrib.auth import get_user_model

from .models import Paciente


class UsuariosFlowTests(TestCase):
	def test_login_and_registro_pages_render(self):
		login_response = self.client.get('/usuarios/login/')
		registro_response = self.client.get('/usuarios/registro/')

		self.assertEqual(login_response.status_code, 200)
		self.assertTemplateUsed(login_response, 'usuarios/login.html')
		self.assertEqual(registro_response.status_code, 200)
		self.assertTemplateUsed(registro_response, 'usuarios/registro.html')

	def test_registro_creates_user_and_paciente_and_logs_in(self):
		response = self.client.post('/usuarios/registro/', {
			'nombre': 'Ana',
			'apellido': 'Gomez',
			'dni': '123456789',
			'correo': 'ana@example.com',
			'telefono': '3001234567',
			'password': 'UnaClaveSegura123!',
			'password2': 'UnaClaveSegura123!',
		})

		self.assertRedirects(response, '/citas/agendar/')
		usuario = get_user_model().objects.get(username='ana@example.com')
		self.assertTrue(usuario.is_authenticated)
		self.assertTrue(Paciente.objects.filter(correo='ana@example.com').exists())
		self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)

	def test_login_with_registered_email(self):
		usuario = get_user_model().objects.create_user(
			username='ana@example.com',
			email='ana@example.com',
			password='UnaClaveSegura123!',
		)

		response = self.client.post('/usuarios/login/', {
			'username': usuario.username,
			'password': 'UnaClaveSegura123!',
		})

		self.assertRedirects(response, '/citas/agendar/')
