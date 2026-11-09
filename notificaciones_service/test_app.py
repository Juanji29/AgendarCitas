import unittest
from unittest.mock import patch

from app import app


class NotificacionesApiTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.payload = {
            'paciente_nombre': 'Ana Gomez',
            'paciente_email': 'ana@example.com',
            'medico_nombre': 'Carlos Perez',
            'especialidad': 'Cardiologia',
            'fecha': '2026-10-01',
            'hora': '10:00',
        }

    def test_confirmacion_responde_200(self):
        respuesta = self.client.post(
            '/api/v2/notificaciones/confirmacion',
            json=self.payload,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json['enviado'])
        self.assertEqual(respuesta.json['canal'], 'consola')
        self.assertIn('Hola Ana Gomez', respuesta.json['mensaje'])

    def test_idioma_es_opcional_y_por_defecto_espanol(self):
        respuesta = self.client.post(
            '/api/v2/notificaciones/confirmacion',
            json=self.payload,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Hola Ana Gomez', respuesta.json['mensaje'])

    @patch('app._enviar_email', return_value='email')
    def test_idioma_ingles_traduce_asunto_y_cuerpo(self, enviar_email):
        respuesta = self.client.post(
            '/api/v2/notificaciones/confirmacion',
            json={**self.payload, 'idioma': 'en'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Hello Ana Gomez', respuesta.json['mensaje'])
        self.assertIn('your appointment with Carlos Perez', respuesta.json['mensaje'])
        self.assertEqual(
            enviar_email.call_args.args[1],
            'Medical appointment confirmation',
        )

    @patch('app._enviar_email', return_value='email')
    @patch('app._obtener_traductor')
    def test_idioma_selecciona_traduccion_para_asunto_y_cuerpo(
        self,
        obtener_traductor,
        enviar_email,
    ):
        obtener_traductor.return_value = lambda texto: f'en:{texto}'
        respuesta = self.client.post(
            '/api/v2/notificaciones/confirmacion',
            json={**self.payload, 'idioma': 'en'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json['mensaje'].startswith('en:Hola'))
        self.assertTrue(enviar_email.call_args.args[1].startswith('en:'))
        obtener_traductor.assert_called_once_with('en')

    def test_idioma_no_soportado_usa_espanol(self):
        respuesta = self.client.post(
            '/api/v2/notificaciones/confirmacion',
            json={**self.payload, 'idioma': 'fr'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Hola Ana Gomez', respuesta.json['mensaje'])

    def test_payload_invalido_responde_400(self):
        respuesta = self.client.post(
            '/api/v2/notificaciones/confirmacion',
            json={'paciente_nombre': 'Ana Gomez'},
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json['error'], 'bad_request')

    @patch('app._enviar_email', side_effect=RuntimeError('SMTP no disponible'))
    def test_fallo_de_envio_responde_500(self, enviar_email):
        respuesta = self.client.post(
            '/api/v2/notificaciones/confirmacion',
            json=self.payload,
        )

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(respuesta.json['error'], 'internal_server_error')
        enviar_email.assert_called_once()


if __name__ == '__main__':
    unittest.main()
