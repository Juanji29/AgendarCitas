"""Pruebas del Patrón Adapter para integraciones externas."""
import json
from datetime import date
from io import BytesIO
from unittest.mock import patch
from urllib import error as urllib_error

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from .integraciones import (
    InfoDiaFestivo,
    NagerDateFestivosAdapter,
    ResumenAliado,
    ResumenHTTPAliadoAdapter,
    ServicioAliadoPort,
)
from .services import CitaService


def _fake_response(payload):
    return BytesIO(json.dumps(payload).encode('utf-8'))


class FestivosAdapterTests(SimpleTestCase):
    def test_traduce_festivo_del_proveedor_a_dominio(self):
        festivos = [
            {'date': '2026-01-01', 'localName': 'Año Nuevo', 'name': "New Year's Day"},
            {'date': '2026-12-25', 'localName': 'Navidad', 'name': 'Christmas Day'},
        ]
        adapter = NagerDateFestivosAdapter(pais='CO')
        with patch('citas.integraciones.urllib_request.urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = _fake_response(festivos)
            resultado = adapter.es_festivo(date(2026, 1, 1))

        self.assertIsInstance(resultado, InfoDiaFestivo)
        self.assertTrue(resultado.es_festivo)
        self.assertEqual(resultado.nombre, 'Año Nuevo')

    def test_fecha_normal_no_es_festivo(self):
        festivos = [{'date': '2026-01-01', 'localName': 'Año Nuevo', 'name': 'NY'}]
        adapter = NagerDateFestivosAdapter(pais='CO')
        with patch('citas.integraciones.urllib_request.urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = _fake_response(festivos)
            resultado = adapter.es_festivo(date(2026, 3, 10))

        self.assertFalse(resultado.es_festivo)

    def test_degradacion_ante_fallo_de_la_api(self):
        adapter = NagerDateFestivosAdapter(pais='CO')
        with patch('citas.integraciones.urllib_request.urlopen',
                   side_effect=urllib_error.URLError('timeout')):
            resultado = adapter.es_festivo(date(2026, 1, 1))

        self.assertFalse(resultado.es_festivo)


class AliadoAdapterTests(SimpleTestCase):
    @override_settings(ALIADO_SERVICE_URL='http://aliado.example')
    def test_traduce_resumen_del_aliado_a_dominio(self):
        payload = {'data': {
            'total': 5,
            'por_estado': {'pendiente': 2, 'confirmada': 3, 'cancelada': 0},
            'por_especialidad': [{'id': 1, 'nombre': 'cardiologia', 'total': 5}],
        }}
        adapter = ResumenHTTPAliadoAdapter()
        with patch('citas.integraciones.urllib_request.urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = _fake_response(payload)
            resultado = adapter.obtener_resumen()

        self.assertIsInstance(resultado, ResumenAliado)
        self.assertTrue(resultado.disponible)
        self.assertEqual(resultado.total, 5)
        self.assertEqual(resultado.detalle['por_estado']['confirmada'], 3)

    @override_settings(ALIADO_SERVICE_URL='')
    def test_sin_url_aliado_no_disponible(self):
        adapter = ResumenHTTPAliadoAdapter()
        resultado = adapter.obtener_resumen()
        self.assertFalse(resultado.disponible)
        self.assertEqual(resultado.total, 0)

    @override_settings(ALIADO_SERVICE_URL='http://aliado.example')
    def test_degradacion_ante_fallo_del_aliado(self):
        adapter = ResumenHTTPAliadoAdapter()
        with patch('citas.integraciones.urllib_request.urlopen',
                   side_effect=urllib_error.URLError('down')):
            resultado = adapter.obtener_resumen()
        self.assertFalse(resultado.disponible)


class _AliadoFalso(ServicioAliadoPort):
    def obtener_resumen(self):
        return ResumenAliado(servicio='fake', total=42, disponible=True)


class ServiceInyeccionDependenciasTests(TestCase):
    def test_consumir_resumen_aliado_acepta_puerto_inyectado(self):
        resultado = CitaService.consumir_resumen_aliado(_AliadoFalso())
        self.assertEqual(resultado.total, 42)
        self.assertTrue(resultado.disponible)

    def test_consultar_festivo_acepta_proveedor_inyectado(self):
        class _FestivoFalso:
            def es_festivo(self, fecha):
                return InfoDiaFestivo(fecha=fecha, es_festivo=True, nombre='Prueba')

        resultado = CitaService.consultar_festivo(date(2026, 1, 1), _FestivoFalso())
        self.assertTrue(resultado.es_festivo)
        self.assertEqual(resultado.nombre, 'Prueba')


class AllyServiceAPITests(APITestCase):
    def test_endpoint_aliado_muestra_servicio_consumido(self):
        with patch(
            'citas.services.IntegracionesFactory.servicio_aliado',
            return_value=_AliadoFalso(),
        ):
            response = self.client.get(reverse('api_v1:aliado'))

        self.assertEqual(response.status_code, 200)
        data = response.data['data']
        self.assertTrue(data['disponible'])
        self.assertEqual(data['total'], 42)



class CeleryTaskTests(TestCase):
    def test_tarea_notificacion_usa_el_notificador(self):
        from datetime import timedelta

        from django.utils import timezone
        from unittest.mock import patch

        from .models import Cita, Especialidad
        from .tasks import enviar_notificacion_confirmacion

        esp, _ = Especialidad.objects.get_or_create(
            nombre='cardiologia', defaults={'duracion_minutos': 30},
        )
        cita = Cita.objects.create(
            paciente_nombre='Ana', paciente_email='ana@example.com',
            medico_nombre='Dr X', especialidad=esp,
            fecha=timezone.localdate() + timedelta(days=1), hora='09:00',
        )

        with patch('citas.factories.NotificadorFactory.crear_notificador') as factory:
            resultado = enviar_notificacion_confirmacion.run(cita.id)

        factory.return_value.notificar_confirmacion.assert_called_once()
        self.assertTrue(resultado['enviado'])

    def test_tarea_notificacion_cita_inexistente(self):
        from .tasks import enviar_notificacion_confirmacion

        resultado = enviar_notificacion_confirmacion.run(999999)
        self.assertFalse(resultado['enviado'])

    def test_tarea_reporte_devuelve_resumen(self):
        from .tasks import generar_reporte_resumen

        resultado = generar_reporte_resumen.run()
        self.assertIn('total', resultado)
        self.assertIn('por_estado', resultado)
