# Agendar Citas Medicas Healthbook

Aplicacion web para gestionar citas medicas. Evoluciona de un monolito Django
hacia un ecosistema hibrido de microservicios (Strangler Pattern), orquestado
por un API Gateway (Nginx), con comunicacion asincrona (Redis + Celery),
integraciones externas mediante el Patron Adapter e internacionalizacion
bilingue (gettext).

## Participantes

- Andres Osorio
- Juan Esteban Jimenez
- Juan Pablo Gaviria

## Funcionalidades

- Registro e inicio de sesion de pacientes.
- Consulta y agendamiento de citas.
- Validacion de fechas y disponibilidad del medico.
- Cancelacion de citas del paciente autenticado.
- Envio asincrono de confirmaciones mediante el microservicio Flask (Celery).
- Catalogo de especialidades servido por un microservicio independiente.
- Bloqueo de citas en dias festivos (API de terceros Nager.Date via Adapter; si la API no responde se permite agendar).
- Consumo del servicio del equipo aliado.
- Interfaz HTML servida por Django, bilingue (es/en).

## Tecnologias

- Python 3.12+ (desarrollo probado en 3.14).
- Django 6.0.7 + Django REST Framework.
- Flask 3.0.3 (microservicios de notificaciones y catalogo).
- Celery 5.4 + Redis 7 (Message Broker).
- Gunicorn 22.0.0 (WSGI de produccion).
- Nginx 1.27 (API Gateway).
- Docker Compose (orquestacion local y en AWS EC2).
- SQLite (monolito y catalogo, bases separadas).

## Arquitectura (Entrega 2)

El sistema se despliega como un ecosistema de contenedores detras de un API
Gateway. El trafico entra por Nginx y se bifurca por ruta (Strangler Pattern).

```text
                         AWS Academy - Instancia EC2
  +-------------------------------------------------------------------+
  |                      Docker Compose network                       |
  |                                                                   |
  |   Cliente/Navegador                                               |
  |          |                                                        |
  |          v                                                        |
  |    +-------------+   Nginx :80 (API Gateway)                      |
  |    |    Nginx    |------------------------------------------------|
  |    +-------------+        |                |            |         |
  |       |        |          |                |            |         |
  |  /(todo)      /api/v2/notificaciones/  /api/v2/catalogo/          |
  |  /api/v1/      |                |            |                    |
  |       v        v                v            v                    |
  |  +---------+  +--------------+  +-----------+                     |
  |  | Django  |  |Flask         |  |Flask      |                     |
  |  | :8000   |  |notificaciones|  |catalogo   |                     |
  |  +---------+  | :5000        |  | :5000     |                     |
  |    |   |      +--------------+  +-----------+                     |
  |    |   |            ^                 |                           |
  |    |   | encola     |                 v                           |
  |    |   v (Celery)   |            catalogo.sqlite3                 |
  |    | +--------+     |                                             |
  |    | | Redis  |<----+----- Celery Worker (procesa tareas)         |
  |    | | :6379  |          (envia notificaciones en segundo plano)  |
  |    | +--------+                                                   |
  |    v                                                              |
  | db.sqlite3                                                        |
  +-------------------------------------------------------------------+
            |                                   |
            v                                   v
   API de terceros (Nager.Date)      Servicio del equipo aliado
   (dias festivos, via Adapter)      (resumen JSON, via Adapter)
```

### Division del trafico en Nginx

- `/api/v2/notificaciones/` y `/api/v2/notificaciones/health` -> Flask notificaciones.
- `/api/v2/catalogo/` y `/api/v2/catalogo/health` -> Flask catalogo.
- `/api/v1/` y el resto del monolito -> Django.

### Microservicios extraidos (Strangler Pattern)

1. **Notificaciones** (`notificaciones_service/`): envia la confirmacion de la
   cita. No accede a la base de datos; recibe los datos por JSON. El monolito
   delega via HTTP a traves de Nginx. Si falla, no se interrumpe el
   agendamiento (resiliencia).
2. **Catalogo** (`catalogo_service/`): expone el catalogo de especialidades con
   **base de datos propia** (SQLite independiente), sembrada desde un fixture
   del monolito (upsert por id). El monolito puede consumirlo para poblar el
   selector y conserva la tabla local como plan B.

## Comunicacion asincrona (Message Broker)

Las notificaciones se procesan en segundo plano con **Celery** usando **Redis**
como broker. Al agendar, el monolito encola la tarea
`enviar_notificacion_confirmacion` y responde de inmediato; el `celery_worker`
la ejecuta y delega al microservicio Flask.

```text
Django --(encola)--> Redis --(consume)--> Celery Worker --> Flask notificaciones
```

También existe `generar_reporte_resumen` para calcular agregados del sistema de
forma asincrona.

## Integraciones externas (Patron Adapter)

El modulo `citas/integraciones.py` define *puertos* (interfaces abstractas) y
*adaptadores* concretos. La logica de negocio depende de la abstraccion, no de
la API externa (Inversion de Dependencias).

- **API de terceros (Nager.Date):** `NagerDateFestivosAdapter` consulta dias
  festivos y avisa al paciente si la fecha elegida es festiva. Ante fallo,
  degrada a "no festivo" sin bloquear.
- **Servicio del equipo aliado:** `ResumenHTTPAliadoAdapter` consume el resumen
  JSON del aliado y lo muestra en `GET /api/v1/aliado/resumen/`.
- **Catalogo:** `CatalogoHTTPAdapter` consume el microservicio de catalogo con
  fallback a la tabla local.

## APIs

### Servicio a proveer

- `GET /api/v1/citas/resumen/`: agregados de citas (total, por especialidad, por
  estado) sin datos personales. No requiere autenticacion.
- `GET /api/v1/info/`: metadatos del sistema (servicio, version, idiomas,
  endpoints) para el descubrimiento entre equipos.

### Servicio a consumir

- `GET /api/v1/aliado/resumen/`: muestra el resumen del equipo aliado consumido
  via Adapter. `disponible=false` si el aliado no responde.

### Microservicio de notificaciones (Flask)

- `POST /api/v2/notificaciones/confirmacion`
- `GET /api/v2/notificaciones/health`

### Microservicio de catalogo (Flask)

- `GET /api/v2/catalogo/especialidades`
- `GET /api/v2/catalogo/especialidades/<id>`
- `GET /api/v2/catalogo/health`

El contrato detallado esta en `docs/contratos_api.md`.

## Ejecucion con Docker Compose

La forma recomendada de ejecutar toda la topologia:

```powershell
docker compose up --build
```

La aplicacion queda disponible mediante Nginx en:

```text
http://localhost/citas/agendar/
```

Comprobar la configuracion sin iniciar los servicios:

```powershell
docker compose config
```

Detener los servicios:

```powershell
docker compose down
```

Servicios que levanta: `redis`, `django`, `celery_worker`, `notificaciones`,
`catalogo` y `nginx`.

## Despliegue en AWS Academy (EC2) - manual

> El despliegue en AWS se realiza a mano. Resumen de pasos:

1. Crear una instancia EC2 (Amazon Linux 2023 o Ubuntu) en AWS Academy y
   asociar una IP elastica.
2. Abrir el puerto 80 (HTTP) en el Security Group. SSH (22) solo para
   administracion.
3. Instalar Docker y el plugin de Compose en la instancia.
4. Clonar el repositorio (rama `main`) en la instancia.
5. Configurar variables de entorno del aliado si aplica
   (`ALIADO_SERVICE_URL`) en `docker-compose.yml`.
6. Ejecutar `docker compose up --build -d`.
7. Verificar:
   - `http://<IP-elastica>/citas/agendar/`
   - `http://<IP-elastica>/api/v2/notificaciones/health`
   - `http://<IP-elastica>/api/v2/catalogo/health`
8. Mantener la instancia encendida para la sustentacion y compartir la IP
   elastica y el enlace del repositorio.

## Ejecucion local sin Docker

Instala las dependencias del monolito:

```powershell
python -m pip install -r requirements.txt
```

Para ejecutar Django sin delegar al microservicio de notificaciones:

```powershell
$env:USAR_MICROSERVICIO_NOTIFICACIONES="False"
python manage.py runserver
```

Sin Celery instalado, las tareas se ejecutan de forma sincrona (modo de
reemplazo), por lo que el monolito funciona igual en desarrollo.

## Internacionalizacion (i18n)

Todo el texto visible usa `gettext`; no hay textos quemados. Los idiomas
soportados son espanol (por defecto) e ingles. Los catalogos `.po`/`.mo` estan
en `locale/` (Django) y `notificaciones_service/locale/` (Flask).

Como no siempre hay `gettext` del sistema, se incluye `compile_po.py`, un
compilador `.po -> .mo` en Python puro:

```powershell
python compile_po.py locale\en\LC_MESSAGES\django.po locale\en\LC_MESSAGES\django.mo
```

El selector de idioma esta en la interfaz (`/i18n/setlang/`).

## Pruebas

Pruebas del microservicio de notificaciones (Flask):

```powershell
python -m unittest discover -s notificaciones_service -p "test_*.py" -v
```

Pruebas del microservicio de catalogo (Flask):

```powershell
python -m unittest discover -s catalogo_service -p "test_*.py" -v
```

Pruebas del monolito (Django):

```powershell
python manage.py collectstatic --noinput
python manage.py test citas usuarios --verbosity 2
```

Cobertura principal:

- API Flask de notificaciones (200/400/500 e i18n).
- API Flask de catalogo (listado, por id, inactiva/inexistente, salud, semilla).
- Resumen agregado e info del sistema.
- Patron Adapter: festivos, aliado y catalogo (incluida la degradacion).
- Tareas asincronas de Celery.
- Flujo de agendamiento, consulta y cancelacion de citas.

## Base de datos

El monolito usa SQLite (`db.sqlite3`) y el catalogo su propia SQLite
(`catalogo.sqlite3` dentro de su contenedor). La separacion de datos del
catalogo refleja la independencia del microservicio. Migrar a un motor
gestionado (p. ej. PostgreSQL) queda como evolucion futura.

## Estructura relevante

- `AgendarCitasMedicas/`: configuracion de Django y la app Celery (`celery.py`).
- `citas/`: modelos, servicios, API, integraciones (`integraciones.py`) y
  tareas (`tasks.py`).
- `notificaciones_service/`: microservicio Flask de notificaciones.
- `catalogo_service/`: microservicio Flask de catalogo con DB propia.
- `nginx.conf`: API Gateway (ruteo entre Django y los microservicios).
- `docker-compose.yml`: orquesta Redis, Django, Celery, Flask x2 y Nginx.
- `compile_po.py`: compilador `.po -> .mo` en Python puro.
- `docs/contratos_api.md`: contratos JSON de las APIs.
