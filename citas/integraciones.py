"""Integraciones externas mediante el Patrón Adapter (Inversión de Dependencias).

El monolito define *puertos* (interfaces abstractas) que expresan lo que el
dominio necesita, sin conocer el formato concreto de cada proveedor externo.
Cada *adaptador* concreto traduce la API externa (API de terceros o servicio
del equipo aliado) al contrato del puerto.

De esta forma, la capa de aplicación depende de la abstracción (el puerto) y no
de los detalles de la API remota: si cambia el proveedor, solo se reemplaza el
adaptador, no la lógica de negocio.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Modelos de dominio (lo que la aplicación entiende, independiente del proveedor)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class InfoDiaFestivo:
    """Resultado normalizado de consultar si una fecha es festiva."""

    fecha: date
    es_festivo: bool
    nombre: str = ''


@dataclass(frozen=True)
class ResumenAliado:
    """Resumen normalizado expuesto por el servicio del equipo aliado."""

    servicio: str
    total: int
    disponible: bool
    detalle: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Puertos (abstracciones): el dominio depende de estas interfaces
# --------------------------------------------------------------------------- #
class ProveedorDiasFestivosPort(ABC):
    """Puerto: consulta si una fecha es día festivo (API de terceros)."""

    @abstractmethod
    def es_festivo(self, fecha: date) -> InfoDiaFestivo:
        raise NotImplementedError


class ServicioAliadoPort(ABC):
    """Puerto: consume el resumen publicado por el equipo aliado."""

    @abstractmethod
    def obtener_resumen(self) -> ResumenAliado:
        raise NotImplementedError


class CatalogoEspecialidadesPort(ABC):
    """Puerto: obtiene el catálogo de especialidades (microservicio)."""

    @abstractmethod
    def listar_activas(self) -> list:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Utilidad HTTP mínima (sin acoplar a una librería concreta)
# --------------------------------------------------------------------------- #
def _get_json(url: str, timeout: int) -> dict:
    peticion = urllib_request.Request(
        url, headers={'Accept': 'application/json'}, method='GET'
    )
    with urllib_request.urlopen(peticion, timeout=timeout) as respuesta:
        return json.loads(respuesta.read().decode('utf-8'))


# --------------------------------------------------------------------------- #
# Adaptadores concretos
# --------------------------------------------------------------------------- #
class NagerDateFestivosAdapter(ProveedorDiasFestivosPort):
    """Adaptador para la API de terceros Nager.Date (días festivos públicos).

    API: https://date.nager.at/api/v3/PublicHolidays/{anio}/{pais}
    Traduce la respuesta (lista de festivos del país) al modelo de dominio
    ``InfoDiaFestivo``. Si la API falla, degrada a "no festivo" para no
    bloquear el agendamiento (resiliencia).
    """

    def __init__(self, pais: str | None = None, timeout: int | None = None,
                 base_url: str | None = None):
        self._pais = pais or getattr(settings, 'FESTIVOS_API_PAIS', 'CO')
        self._timeout = timeout or getattr(settings, 'FESTIVOS_API_TIMEOUT', 3)
        self._base_url = (
            base_url or getattr(settings, 'FESTIVOS_API_URL', 'https://date.nager.at')
        ).rstrip('/')

    def es_festivo(self, fecha: date) -> InfoDiaFestivo:
        url = f'{self._base_url}/api/v3/PublicHolidays/{fecha.year}/{self._pais}'
        try:
            festivos = _get_json(url, self._timeout)
        except (urllib_error.URLError, TimeoutError, ValueError) as error:
            logger.warning('API de festivos no disponible: %s', error)
            return InfoDiaFestivo(fecha=fecha, es_festivo=False)

        objetivo = fecha.isoformat()
        for festivo in festivos or []:
            if festivo.get('date') == objetivo:
                return InfoDiaFestivo(
                    fecha=fecha,
                    es_festivo=True,
                    nombre=festivo.get('localName') or festivo.get('name', ''),
                )
        return InfoDiaFestivo(fecha=fecha, es_festivo=False)


class ResumenHTTPAliadoAdapter(ServicioAliadoPort):
    """Adaptador para el servicio del equipo aliado.

    El aliado expone un endpoint JSON equivalente a nuestro
    ``GET /api/v1/citas/resumen/`` (sobre ``{"data": {...}}``). Este adaptador
    traduce ese formato al modelo de dominio ``ResumenAliado``. La URL base se
    toma de ``ALIADO_SERVICE_URL``.
    """

    def __init__(self, base_url: str | None = None, timeout: int | None = None,
                 nombre: str | None = None):
        self._base_url = (
            base_url or getattr(settings, 'ALIADO_SERVICE_URL', '')
        ).rstrip('/')
        self._timeout = timeout or getattr(settings, 'ALIADO_SERVICE_TIMEOUT', 3)
        self._nombre = nombre or getattr(settings, 'ALIADO_SERVICE_NOMBRE', 'equipo-aliado')

    def obtener_resumen(self) -> ResumenAliado:
        if not self._base_url:
            logger.info('ALIADO_SERVICE_URL no configurado; aliado no disponible.')
            return ResumenAliado(servicio=self._nombre, total=0, disponible=False)

        url = f'{self._base_url}/api/v1/citas/resumen/'
        try:
            cuerpo = _get_json(url, self._timeout)
        except (urllib_error.URLError, TimeoutError, ValueError) as error:
            logger.warning('Servicio del aliado no disponible: %s', error)
            return ResumenAliado(servicio=self._nombre, total=0, disponible=False)

        data = cuerpo.get('data', cuerpo) if isinstance(cuerpo, dict) else {}
        return ResumenAliado(
            servicio=self._nombre,
            total=int(data.get('total', 0) or 0),
            disponible=True,
            detalle={
                'por_estado': data.get('por_estado', {}),
                'por_especialidad': data.get('por_especialidad', []),
            },
        )



class CatalogoHTTPAdapter(CatalogoEspecialidadesPort):
    """Adaptador para el microservicio de catálogo (Flask + DB propia).

    Consume ``GET /api/v2/catalogo/especialidades`` y devuelve la lista de
    especialidades activas. Si falla (timeout, red o 503), devuelve ``None``
    para que la capa de aplicación use su plan B: la tabla local.
    """

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self._base_url = (
            base_url or getattr(settings, 'CATALOGO_SERVICE_URL', '')
        ).rstrip('/')
        self._timeout = timeout or getattr(settings, 'CATALOGO_SERVICE_TIMEOUT', 3)

    def listar_activas(self):
        if not self._base_url:
            return None
        url = f'{self._base_url}/api/v2/catalogo/especialidades'
        try:
            cuerpo = _get_json(url, self._timeout)
        except (urllib_error.URLError, TimeoutError, ValueError) as error:
            logger.warning('Catálogo no disponible, se usará la tabla local: %s', error)
            return None
        if not isinstance(cuerpo, dict):
            return None
        return cuerpo.get('data', [])
