from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Cita, Especialidad
from usuarios.models import Paciente


class AppointmentAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='ana@example.com',
            email='ana@example.com',
            password='UnaClaveSegura123!',
        )
        self.client.force_authenticate(self.user)
        self.specialty = Especialidad.objects.create(
            nombre='Cardiologia',
            duracion_minutos=30,
        )
        self.appointment_url = reverse('api_v1:citas')

    def appointment_payload(self, **overrides):
        payload = {
            'paciente_nombre': 'Ana Gomez',
            'paciente_email': 'ana@example.com',
            'medico_nombre': 'Carlos Perez',
            'especialidad': self.specialty.pk,
            'fecha': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'hora': '10:00',
            'motivo': 'Consulta',
        }
        payload.update(overrides)
        return payload

    def test_create_appointment_returns_201_and_serialized_data(self):
        with patch('citas.services.NotificadorFactory.crear_notificador') as factory:
            response = self.client.post(
                self.appointment_url,
                self.appointment_payload(),
                format='json',
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['data']['paciente_nombre'], 'Ana Gomez')
        self.assertEqual(response.data['data']['especialidad']['nombre'], 'Cardiologia')
        self.assertEqual(Cita.objects.count(), 1)
        factory.return_value.notificar_confirmacion.assert_called_once()

    def test_invalid_appointment_payload_returns_400(self):
        response = self.client.post(
            self.appointment_url,
            {'paciente_nombre': 'Ana Gomez'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'validation_error')
        self.assertIn('fecha', response.data['detail'])

    def test_business_validation_error_returns_400(self):
        payload = self.appointment_payload(
            fecha=(timezone.localdate() - timedelta(days=1)).isoformat(),
        )

        response = self.client.post(self.appointment_url, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'validation_error')

    def test_occupied_appointment_slot_returns_409(self):
        payload = self.appointment_payload()
        Cita.objects.create(
            paciente_nombre='Otra Persona',
            medico_nombre=payload['medico_nombre'],
            especialidad=self.specialty,
            fecha=payload['fecha'],
            hora=payload['hora'],
        )

        response = self.client.post(self.appointment_url, payload, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['error'], 'conflict')

    def test_cancel_unknown_appointment_returns_404(self):
        response = self.client.post(
            reverse('api_v1:cancelar_cita', kwargs={'appointment_id': 999}),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['error'], 'not_found')

    def test_cancelling_already_cancelled_appointment_returns_409(self):
        appointment = Cita.objects.create(
            paciente_nombre='Ana Gomez',
            paciente_email=self.user.email,
            medico_nombre='Carlos Perez',
            especialidad=self.specialty,
            fecha=timezone.localdate() + timedelta(days=1),
            hora='10:00',
            estado=Cita.ESTADO_CANCELADA,
        )

        response = self.client.post(
            reverse('api_v1:cancelar_cita', kwargs={'appointment_id': appointment.pk}),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['error'], 'conflict')


class PatientRegistrationAPITests(APITestCase):
    url = reverse('api_v1:registro')

    def registration_payload(self, **overrides):
        payload = {
            'nombre': 'Ana',
            'apellido': 'Gomez',
            'dni': '123456789',
            'correo': 'ana@example.com',
            'telefono': '3001234567',
            'password': 'UnaClaveSegura123!',
            'password2': 'UnaClaveSegura123!',
        }
        payload.update(overrides)
        return payload

    def test_register_patient_returns_201_without_password(self):
        response = self.client.post(
            self.url,
            self.registration_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['data']['email'], 'ana@example.com')
        self.assertNotIn('password', response.data['data'])
        self.assertTrue(Paciente.objects.filter(correo='ana@example.com').exists())

    def test_password_mismatch_returns_400(self):
        response = self.client.post(
            self.url,
            self.registration_payload(password2='different-password'),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'validation_error')

    def test_duplicate_account_returns_409(self):
        get_user_model().objects.create_user(
            username='ana@example.com',
            email='ana@example.com',
            password='UnaClaveSegura123!',
        )

        response = self.client.post(
            self.url,
            self.registration_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['error'], 'conflict')
