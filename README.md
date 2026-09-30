# Agendar Citas Medicas Healthbook

Aplicacion web para gestionar citas medicas. El sistema conserva un monolito
Django para la agenda y utiliza un microservicio Flask para las notificaciones
de confirmacion.

## Participantes

- Andres Osorio
- Juan Esteban Jimenez
- Juan Pablo Gaviria

## Funcionalidades

- Registro e inicio de sesion de pacientes.
- Consulta y agendamiento de citas.
- Validacion de fechas y disponibilidad del medico.
- Cancelacion de citas del paciente autenticado.
- Envio de confirmaciones mediante el microservicio Flask.
- Interfaz HTML servida por Django.

## Tecnologias

- Python 3.13 o compatible.
- Django 6.0.7.
- Flask 3.0.3.
- Gunicorn 22.0.0.
- Nginx 1.27.
- Docker Compose.
- SQLite.

## Decision de extraccion

No todas las funcionalidades deben convertirse en microservicios. Se evaluaron
los modulos con una escala de 1 a 5:

| Funcionalidad | Frecuencia de cambio | Latencia o consumo | Independencia de datos | Decision |
| --- | ---: | ---: | ---: | --- |
| Agendar y validar disponibilidad | 2 | 2 | 1 | Permanece en Django |
| Consultar citas | 2 | 2 | 1 | Permanece en Django |
| Cancelar cita | 2 | 1 | 1 | Permanece en Django |
| Enviar confirmacion por correo | 3 | 4 | 5 | Se extrae a Flask |

La funcionalidad seleccionada fue el envio de notificaciones. Depende de un
proveedor externo, puede introducir latencia y no necesita consultar
directamente la base de datos de citas. La agenda y la validacion de
disponibilidad permanecen en Django porque estan fuertemente acopladas a sus
modelos y transacciones.

## Arquitectura Strangler Pattern

```text
Cliente
   |
   v
Nginx :80
   |------------------------------|
   v                              v
Django :8000                 Flask :5000
   |                              |
   v                              v
SQLite                 Servicio SMTP o consola
```

El trafico se divide por ruta:

- `/api/v1/` y el resto de las rutas del monolito van a Django.
- `/api/v2/notificaciones/` va al microservicio Flask.
- `/api/v2/notificaciones/health` expone el healthcheck de Flask.

Cuando se ejecuta con Docker Compose, Django utiliza
`http://nginx/api/v2/notificaciones/confirmacion`. Por tanto, el flujo real de
una notificacion es:

```text
Django -> Nginx -> Flask -> SMTP o consola
```

Si Flask no responde, Django registra el error y no cancela la cita que ya fue
guardada.

## API de notificaciones

### `POST /api/v2/notificaciones/confirmacion`

Recibe JSON con los campos requeridos:

```json
{
  "paciente_nombre": "Ana Gomez",
  "paciente_email": "ana@example.com",
  "medico_nombre": "Carlos Perez",
  "especialidad": "Cardiologia",
  "fecha": "2026-10-01",
  "hora": "10:00"
}
```

Respuestas principales:

- `200`: notificacion procesada.
- `400`: JSON invalido o faltan campos requeridos.
- `500`: error interno al procesar o enviar la notificacion.

### `GET /api/v2/notificaciones/health`

Devuelve el estado del microservicio:

```json
{
  "status": "ok",
  "service": "notificaciones"
}
```

## Ejecucion local

Instala las dependencias del monolito:

```powershell
python -m pip install -r requirements.txt
```

Para ejecutar Django localmente sin Docker, desactiva la delegacion
temporalmente:

```powershell
$env:USAR_MICROSERVICIO_NOTIFICACIONES="False"
python manage.py runserver
```

La aplicacion queda disponible en:

```text
http://127.0.0.1:8000/citas/agendar/
```

## Ejecucion con Docker Compose

La forma recomendada para ejecutar toda la topologia es:

```powershell
docker compose up --build
```

La aplicacion queda disponible mediante Nginx en:

```text
http://localhost/citas/agendar/
```

Para comprobar la configuracion sin iniciar los servicios:

```powershell
docker compose config
```

Para detener los servicios:

```powershell
docker compose down
```

El microservicio usa modo consola cuando `SMTP_HOST` no esta configurado. Para
usar SMTP, deben proporcionarse `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD` y `FROM_EMAIL` al servicio `notificaciones`.

## Pruebas

Pruebas del microservicio Flask:

```powershell
python -m unittest discover -s notificaciones_service -p "test_*.py" -v
```

Antes de ejecutar las pruebas de Django, genera los archivos estaticos:

```powershell
python manage.py collectstatic --noinput
python manage.py test citas --verbosity 2
```

Las pruebas cubren:

- Respuesta `200` de la API Flask.
- Respuesta `400` para payload invalido.
- Respuesta `500` para errores internos.
- Comunicacion de Django hacia Flask a traves de Nginx.
- Flujo de agendamiento, consulta y cancelacion de citas.

## Base de datos

Actualmente el proyecto utiliza SQLite en `db.sqlite3`. La base de datos no es
un servicio independiente de Docker y no fue migrada a PostgreSQL en esta
iteracion. Separarla requiere una migracion de datos y una decision sobre
persistencia y operacion, por lo que queda como evolucion futura.

## Estructura relevante

- `AgendarCitasMedicas/`: configuracion principal de Django.
- `citas/`: modelos, formularios, vistas y servicios de citas.
- `notificaciones_service/`: API Flask y su Dockerfile independiente.
- `nginx.conf`: enrutamiento entre Django y Flask.
- `Dockerfile`: imagen del monolito Django.
- `docker-compose.yml`: orquestacion de Django, Flask y Nginx.
- `db.sqlite3`: base de datos local actual.
- `static/`: archivos estaticos fuente.
- `staticfiles/`: archivos generados por `collectstatic`.
