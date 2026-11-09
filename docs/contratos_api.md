# Contratos JSON: catálogo y resumen de citas

Este documento define dos contratos para la Entrega 2 a partir de los modelos
y endpoints que existen en el repositorio. Los contratos son una especificación:
no implican que `catalogo_service` ni el resumen de citas ya estén
implementados.

## Convenciones

- Las respuestas exitosas usan el sobre `{"data": ...}`, consistente con la API
  de la Entrega 1.
- Los errores conservan el formato actual de la API del monolito:
  `{"error": "<codigo>", "detail": "<mensaje>"}`. No se usa un objeto de error
  anidado.
- Los IDs son enteros. Las fechas y marcas de tiempo usan ISO 8601; las marcas
  de tiempo se expresan en UTC.
- Una colección sin elementos responde `200` con `"data": []`.

## 1. `catalogo_service`

Nuevo microservicio Flask, con base de datos propia, accesible mediante
`CATALOGO_SERVICE_URL`. Dentro de Docker escucha en el puerto `5000`. Nginx
debe enrutar `/api/v2/catalogo/` al servicio; el healthcheck interno se sirve
en `/health`.

El catálogo refleja el modelo actual `Especialidad`:

| Campo | Tipo JSON | Significado |
| --- | --- | --- |
| `id` | entero | Identificador, sincronizado con el ID local del monolito |
| `nombre` | cadena | Nombre/identificador legible actual, por ejemplo `pediatria` |
| `duracion_minutos` | entero | Duración asociada a la especialidad |
| `requiere_referido` | booleano | Indica si requiere referido |
| `activa` | booleano | Indica si está activa |

No se incluye `codigo`: el modelo no tiene ese campo. Tampoco se define un
recurso o endpoint de `servicios`, ya que no existe un modelo `Servicio`.

### `GET /api/v2/catalogo/especialidades`

Lista las especialidades activas. La API E1 actual obtiene su listado mediante
`CitaService.obtener_especialidades()`, que filtra `activa=True`; el catálogo
debe comportarse igual para que el selector no ofrezca opciones inactivas.

**Parámetros:** ninguno.

**200**

```json
{
  "data": [
    {
      "id": 1,
      "nombre": "cardiologia",
      "duracion_minutos": 30,
      "requiere_referido": true,
      "activa": true
    },
    {
      "id": 2,
      "nombre": "pediatria",
      "duracion_minutos": 25,
      "requiere_referido": false,
      "activa": true
    }
  ]
}
```

**Errores**

- `503 Service Unavailable`: el catálogo no puede acceder a su base de datos o
  no está listo.

```json
{
  "error": "service_unavailable",
  "detail": "El catálogo no está disponible temporalmente."
}
```

### `GET /api/v2/catalogo/especialidades/<int:id>`

Obtiene una especialidad activa por ID. Al usar el convertidor `<int:id>` de
Flask, una ruta cuyo ID no sea numérico no coincide y responde `404`. Las
especialidades inactivas se tratan como no encontradas, igual que las opciones
ocultas en el listado público.

**Parámetros de ruta:** `id`, entero positivo.

**200**

```json
{
  "data": {
    "id": 2,
    "nombre": "pediatria",
    "duracion_minutos": 25,
    "requiere_referido": false,
    "activa": true
  }
}
```

**Errores**

- `404 Not Found`: ID no numérico, inexistente o perteneciente a una
  especialidad inactiva.
- `503 Service Unavailable`: el catálogo no puede acceder a su base de datos o
  no está listo.

404:

```json
{
  "error": "not_found",
  "detail": "No se encontró una especialidad activa con ese id."
}
```

503:

```json
{
  "error": "service_unavailable",
  "detail": "El catálogo no está disponible temporalmente."
}
```

### `GET /health`

Healthcheck interno del microservicio. Si se publica detrás de Nginx, la ruta
pública será `GET /api/v2/catalogo/health`, reescrita hacia `/health` en Flask.

**200**

```json
{
  "status": "ok",
  "service": "catalogo"
}
```

**503:** proceso activo pero no listo para atender solicitudes, por ejemplo si
su base de datos no está disponible.

```json
{
  "error": "service_unavailable",
  "detail": "El catálogo no está listo."
}
```

### Sincronización transitoria de datos

Durante esta etapa del Strangler, el catálogo tendrá su propia base de datos,
mientras el monolito conserva `Especialidad` local. Las relaciones
`Cita.especialidad` (FK) y `Medico.especialidades` (M2M) permanecen locales.
Por ello, la API del catálogo alimenta el selector, pero el monolito valida y
persiste las citas contra sus tablas locales.

Procedimiento para sembrar el catálogo con el contenido del monolito:

1. Exportar las especialidades locales con sus claves primarias:

   ```powershell
   python manage.py dumpdata citas.Especialidad --indent 2 --output catalogo_service/data/especialidades.json
   ```

   Django incluye el `pk` de cada registro en el fixture. Ese valor debe
   conservarse como `id` al importar la semilla al catálogo; no se deben
   generar IDs nuevos ni reasignarlos.
2. Al arrancar `catalogo_service`, cargar ese fixture como semilla usando una
   importación repetible (upsert por `id`) y guardar los cinco campos del
   contrato. Los registros que ya existan deben actualizarse por ID, no
   duplicarse.
3. Después de cada exportación/carga, verificar ambos lados: consultar en el
   monolito y en el catálogo las columnas `id`, `nombre`, `duracion_minutos`,
   `requiere_referido` y `activa`, ordenadas por `id`; comparar las filas
   completas y el conteo. La sincronización solo está confirmada si los
   conteos coinciden y cada fila tiene los mismos valores para esos campos.
   También debe verificarse que los IDs exportados no cambiaron durante la
   importación.

Esta estrategia es transitoria y mantiene **dos fuentes de datos**. Entre
cargas pueden divergir los nombres, duraciones, el estado `activa` o los IDs.
Una especialidad visible en el catálogo podría no existir o estar inactiva en
la base local; por eso el monolito valida el ID al recibir el formulario y no
confía exclusivamente en la respuesta remota. La exportación y carga deben
repetirse al cambiar el catálogo. La estrategia futura debe definir una única
fuente de verdad y la migración de las relaciones locales.

## 2. Resumen de citas en el monolito

### `GET /api/v1/citas/resumen/`

Endpoint agregado del monolito. Devuelve conteos y no expone nombres, correos ni
otros datos personales de pacientes.

**Autenticación:** no requerida (`AllowAny`), porque la respuesta contiene
únicamente datos agregados.

**Parámetros:** ninguno.

**200**

```json
{
  "data": {
    "total": 23,
    "por_especialidad": [
      {
        "id": 1,
        "nombre": "cardiologia",
        "total": 8
      },
      {
        "id": 2,
        "nombre": "pediatria",
        "total": 15
      }
    ],
    "por_estado": {
      "pendiente": 7,
      "confirmada": 12,
      "cancelada": 4
    },
    "generado_en": "2026-11-09T22:30:00Z"
  }
}
```

`total` incluye todas las citas, también las canceladas. `por_especialidad`
agrupa por la FK local de `Cita` e incluye el ID y nombre local de la
especialidad; se recomienda incluir solo especialidades con citas. `por_estado`
incluye todos los estados definidos por el modelo (`pendiente`, `confirmada`,
`cancelada`), incluso cuando su conteo sea cero. Por tanto, la suma de los
conteos por estado debe coincidir con `total`. `generado_en` es la hora UTC en
que se construyó la respuesta.

**Errores:** no tiene parámetros que requieran validación y no requiere
autenticación; por ello no define respuestas `400` ni `401`. Un resumen no usa
`404` ni `503` como parte de su contrato.

## Reglas del cliente del monolito para el catálogo

- Leer la URL base desde la variable de entorno `CATALOGO_SERVICE_URL`. En
  Docker Compose, el valor de ejemplo es `http://nginx`; el cliente agrega la
  ruta `/api/v2/catalogo/especialidades`.
- Limitar la llamada HTTP a un timeout de **2–3 segundos**.
- Si la solicitud falla por timeout, error de red o respuesta `503`, usar como
  plan B la tabla local `Especialidad` para poblar el selector. La consulta local
  debe ofrecer solo registros activos.
- Al enviar el formulario, validar el ID escogido contra la tabla local
  `Especialidad` y las asociaciones locales `Medico.especialidades`. Si el ID
  no existe, está inactivo o no corresponde al médico seleccionado, devolver un
  error de formulario comprensible; nunca propagar el fallo como `500`.
- No crear una especialidad local automáticamente a partir de una respuesta
  remota. El catálogo no reemplaza las FK/M2M locales durante esta etapa.

## Compatibilidad con la API de Entrega 1

Se conserva `GET /api/v1/especialidades/` sin cambios para no romper la E1 ni
sus pruebas. Actualmente devuelve `{"data": [...]}` y filtra por `activa=True`.
El nuevo catálogo expone una lista equivalente para permitir la migración
gradual del selector. El resumen propuesto es una ruta nueva y no duplica
ninguna ruta E1 existente.
