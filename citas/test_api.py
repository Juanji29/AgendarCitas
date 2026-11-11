from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .integraciones import InfoDiaFestivo
from .models import Cita, Especialidad
from usuarios.models import Medico, Paciente


class AppointmentAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='ana@example.com',
            email='ana@example.com',
            password='UnaClaveSegura123!',
        )
        self.client.force_authenticate(self.user)
        # Aísla las pruebas de la API real de festivos: por defecto, día hábil.
        festivos_patcher = patch('citas.services.IntegracionesFactory.proveedor_festivos')
        self.proveedor_festivos = festivos_patcher.start().return_value
        self.proveedor_festivos.es_festivo.side_effect = (
            lambda fecha: InfoDiaFestivo(fecha=fecha, es_festivo=False)
        )
        self.addCleanup(festivos_patcher.stop)
        self.specialty = Especialidad.objects.create(
            nombre='Cardiologia',
            duracion_minutos=30,
        )
        self.doctor = Medico.objects.create(
            nombre='Carlos',
            apellido='Perez',
            dni='987654321',
            correo='carlos@example.com',
            telefono='3009876543',
            registro_medico='RM-001',
        )
        self.doctor.especialidades.add(self.specialty)
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

    def test_create_appointment_on_holiday_returns_400(self):
        self.proveedor_festivos.es_festivo.side_effect = (
            lambda fecha: InfoDiaFestivo(fecha=fecha, es_festivo=True, nombre='Día de prueba')
        )

        response = self.client.post(
            self.appointment_url,
            self.appointment_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'validation_error')
        self.assertIn('Día de prueba', response.data['detail'])
        self.assertEqual(Cita.objects.count(), 0)

    def test_invalid_appointment_payload_returns_400(self):
        response = self.client.post(
            self.appointment_url,
            {'paciente_nombre': 'Ana Gomez'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'validation_error')
        self.assertIn('fecha', response.data['detail'])

    def test_list_doctors_filters_by_specialty(self):
        other_specialty = Especialidad.objects.create(
            nombre='Pediatria',
            duracion_minutos=25,
        )
        other_doctor = Medico.objects.create(
            nombre='Maria',
            apellido='Lopez',
            dni='123456789',
            correo='maria@example.com',
            telefono='3001234567',
            registro_medico='RM-002',
        )
        other_doctor.especialidades.add(other_specialty)

        response = self.client.get(
            reverse('api_v1:medicos'),
            {'especialidad': self.specialty.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [doctor['id'] for doctor in response.data['data']],
            [self.doctor.pk],
        )

    def test_list_doctors_requires_a_valid_specialty_id(self):
        response = self.client.get(reverse('api_v1:medicos'))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'validation_error')

    def test_business_validation_error_returns_400(self):
        payload = self.appointment_payload(
            fecha=(timezone.localdate() - timedelta(days=1)).isoformat(),
        )

        response = self.client.post(self.appointment_url, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'validation_error')

    def test_doctor_must_be_associated_with_selected_specialty(self):
        other_specialty = Especialidad.objects.create(
            nombre='Pediatria',
            duracion_minutos=25,
        )

        response = self.client.post(
            self.appointment_url,
            self.appointment_payload(especialidad=other_specialty.pk),
            format='json',
        )

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


class AppointmentSummaryAPITests(APITestCase):
    def setUp(self):
        self.cardio, _ = Especialidad.objects.get_or_create(
            nombre='cardiologia', defaults={'duracion_minutos': 30},
        )
        self.pedia, _ = Especialidad.objects.get_or_create(
            nombre='pediatria', defaults={'duracion_minutos': 25},
        )
        # Evita contar citas sembradas por otras pruebas/migraciones.
        Cita.objects.all().delete()
        base = timezone.localdate() + timedelta(days=1)
        Cita.objects.create(
            paciente_nombre='A', medico_nombre='Dr X', especialidad=self.cardio,
            fecha=base, hora='09:00', estado=Cita.ESTADO_PENDIENTE,
        )
        Cita.objects.create(
            paciente_nombre='B', medico_nombre='Dr X', especialidad=self.cardio,
            fecha=base, hora='10:00', estado=Cita.ESTADO_CONFIRMADA,
        )
        Cita.objects.create(
            paciente_nombre='C', medico_nombre='Dr Y', especialidad=self.pedia,
            fecha=base, hora='11:00', estado=Cita.ESTADO_CANCELADA,
        )
        self.url = reverse('api_v1:resumen')

    def test_resumen_no_requiere_autenticacion(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_resumen_devuelve_agregados_sin_pii(self):
        response = self.client.get(self.url)
        data = response.data['data']

        self.assertEqual(data['total'], 3)
        # La suma por estado coincide con el total (todos los estados presentes).
        self.assertEqual(sum(data['por_estado'].values()), 3)
        self.assertEqual(data['por_estado']['pendiente'], 1)
        self.assertEqual(data['por_estado']['confirmada'], 1)
        self.assertEqual(data['por_estado']['cancelada'], 1)
        # No se exponen datos personales.
        texto = str(response.content)
        self.assertNotIn('paciente_nombre', texto)
        self.assertIn('generado_en', data)

    def test_resumen_agrupa_por_especialidad(self):
        response = self.client.get(self.url)
        por_esp = {fila['nombre']: fila['total'] for fila in response.data['data']['por_especialidad']}
        self.assertEqual(por_esp['cardiologia'], 2)
        self.assertEqual(por_esp['pediatria'], 1)


class SystemInfoAPITests(APITestCase):
    def test_info_devuelve_metadatos_del_servicio(self):
        response = self.client.get(reverse('api_v1:info'))
        self.assertEqual(response.status_code, 200)
        data = response.data['data']
        self.assertEqual(data['servicio'], 'healthbook-citas')
        self.assertIn('es', data['idiomas'])
        self.assertIn('en', data['idiomas'])
        self.assertIn('resumen', data['endpoints'])
