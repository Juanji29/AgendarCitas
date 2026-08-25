# Avance de Arquitectura — Proyecto AgendarCitas

**Entrega No. 1 — Arquitectura de Software 2026**
**Última actualización:** 25 de agosto de 2026

Este documento explica, con nivel de detalle suficiente para que cualquiera del
equipo pueda continuar sin perder contexto, qué arquitectura tiene el proyecto,
qué se implementó en esta sesión de trabajo, y qué falta por hacer para cumplir
con la rúbrica de la entrega.

---

## 1. Objetivo de la entrega (resumen)

Consolidar el núcleo del sistema implementando entre el **50% y 60% de las
clases de dominio**, exponiéndolo mediante **Django Rest Framework**, con
desacoplamiento total vía **Service Layer** y **patrones creacionales**
(Builder y Factory).

**Advertencia crítica de la rúbrica:** cualquier lógica de negocio (cálculos,
validaciones, reglas) dentro de `views.py` o en métodos de un `Model` que no
sean de persistencia, penaliza la nota de la sección SOLID en un **50%**. Todo
el trabajo de este proyecto está guiado por evitar esa penalización.

---

## 2. Arquitectura actual: cómo fluye una petición

Cuando alguien agenda una cita, el flujo pasa por estas capas, en este orden:

### 2.1. `views.py` — capa de presentación (HTML por ahora, DRF pendiente)

`AgendarCitaView` extiende `django.views.View`. El método `get()` muestra el
formulario vacío. El método `post()` valida el formulario y le delega **todo**
el trabajo de negocio a `CitaService.agendar_cita()`. La vista solo decide qué
renderizar según el resultado (éxito → redirect, error → mostrar el form con
el error). No contiene ninguna regla de negocio — esto es intencional y es
exactamente lo que pide la rúbrica.

### 2.2. `forms.py` — validación de entrada

`CitaForm` es un `ModelForm` sobre `Cita`. Valida tipos de datos básicos
(formato de fecha, de email, campos requeridos) antes de que los datos lleguen
al flujo de negocio real. No decide nada de negocio, solo filtra datos mal
formados.

### 2.3. `services.py` — Service Layer (capa de aplicación)

`CitaService.agendar_cita(datos)` es el orquestador central. En orden:

1. Le pide al `CitaBuilder` que construya una `Cita` válida.
2. Llama a `_validar_disponibilidad()` (método propio del Service) para
   comprobar que el médico no tenga ya una cita en ese horario.
3. Guarda la cita.
4. Le pide a `NotificadorFactory` el notificador correcto y notifica al
   paciente.

`CitaService` no sabe *cómo* se construye una cita válida ni *cómo* se envía
una notificación — solo conoce el orden de los pasos. Esto es SRP aplicado
correctamente: una sola razón para cambiar (el flujo de agendamiento).

### 2.4. `builders.py` — patrón Builder

`CitaBuilder` ensambla una `Cita` paso a paso de forma fluida
(`.con_paciente().con_medico().con_especialidad()...build()`), y `build()`
llama a `full_clean()` antes de devolver el objeto, garantizando que nunca
salga de ahí una `Cita` inválida.

### 2.5. `factories.py` + `notificaciones.py` — patrón Factory

`NotificadorFactory.crear_notificador()` decide, según el setting
`NOTIFICAR_POR_EMAIL`, si devuelve un `EmailNotificador` o un
`NotificadorConsola`. Ambos implementan la interfaz abstracta `Notificador`
(`ABC`). `CitaService` nunca sabe cuál de las dos implementaciones recibió,
solo confía en el contrato de la interfaz. Esto cumple el requisito de
"gestionar al menos una dependencia externa" (el envío de correo).

### 2.6. `models.py` — capa de dominio y persistencia

Los modelos contienen únicamente validaciones intrínsecas a la propia entidad
(por ejemplo, `Cita.clean()` impide fechas pasadas). Cualquier regla que
dependa de la relación entre entidades (como la política de duración por
especialidad) NO debe vivir aquí ni en el Builder — debe vivir en la entidad
que la posee (ver sección 3).

---

## 3. Qué se implementó en esta sesión: la entidad `Especialidad`

### 3.1. Por qué se hizo primero

De las entidades nuevas necesarias (`Especialidad`, `Medico`, `Paciente`),
`Especialidad` no depende de ninguna otra y además resuelve un problema de
diseño que ya existía: el Builder tenía hardcodeada una tabla de políticas de
negocio (duración de cita y si requiere referido, por especialidad) que no
debería estar ahí.

### 3.2. El modelo

```python
class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    duracion_minutos = models.PositiveSmallIntegerField()
    requiere_referido = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Especialidades'

    def __str__(self):
        return self.nombre
```

- `nombre` es único: antes, `"Cardiologia"` y `"cardiologia"` en `Cita`
  hubieran sido dos valores distintos para la base de datos. Ahora no puede
  pasar.
- `duracion_minutos` y `requiere_referido` son la política de negocio movida
  desde el Builder — ahora son datos propios de la entidad que describen.
- `activa` permite desactivar una especialidad sin borrarla ni romper el
  historial de citas que ya la referencian (mejor que un `DELETE` físico).

Se sembraron 4 especialidades (mismos valores que existían hardcodeados
antes): `cardiologia` (30 min, requiere referido), `pediatria` (25 min),
`dermatologia` (20 min), `medicina general` (20 min).

### 3.3. La técnica de migración: expand-contract

`Cita.especialidad` era un `CharField` con datos ya guardados. Convertirlo
directo a `ForeignKey` hubiera arriesgado perder esa información. Se usó el
patrón **expand-contract**, en 3 migraciones separadas (esta técnica es una
práctica profesional real, no solo para la tarea — vale la pena citarla en la
Wiki Técnica como justificación de diseño):

1. **Expand** (`0006`): se agrega `especialidad_fk` (FK nullable) sin tocar
   el campo viejo. Ambos conviven temporalmente.
2. **Migrate data** (`0007`): una migración de datos (`RunPython`) recorre
   todas las citas existentes y llena `especialidad_fk` buscando la
   `Especialidad` cuyo `nombre` coincide (comparando con `.strip().lower()`)
   con el valor viejo. Antes de escribir esta migración se verificaron los
   valores reales en la base (se encontraron variantes de mayúsculas como
   `'Cardiologia'`, que sí calzaron correctamente con la comparación
   normalizada).
3. **Contract** (`0008`): se borra el campo `especialidad` viejo, se
   renombra `especialidad_fk` a `especialidad`, y se vuelve `null=False`.
   `on_delete=models.PROTECT` — impide borrar una especialidad si ya tiene
   citas asociadas, en vez de cascadear el borrado.

Resultado verificado: las 4 citas existentes conservaron su especialidad y
sus valores de `duracion_minutos`/`requiere_referido` correctamente.

### 3.4. Limpieza del Builder

Antes, `con_especialidad()` consultaba un diccionario hardcodeado para decidir
la política. Ahora que recibe una instancia real de `Especialidad`, simplemente
copia los valores que ya trae el objeto:

```python
def con_especialidad(self, especialidad):
    self._cita.especialidad = especialidad
    self._cita.duracion_minutos = especialidad.duracion_minutos
    self._cita.requiere_referido = especialidad.requiere_referido
    return self
```

El diccionario `_POLITICAS_ESPECIALIDAD` y `_POLITICA_POR_DEFECTO` fueron
eliminados por completo. El Builder ya no decide política de negocio, solo la
aplica — la decisión vive donde debe vivir: en `Especialidad`.

`services.py` no necesitó cambios: como `CitaForm` es un `ModelForm`, en
cuanto el campo del modelo pasó de `CharField` a `ForeignKey`, Django generó
automáticamente un `ModelChoiceField`, así que `datos['especialidad']` ya
llega como instancia de `Especialidad`, no como string.

### 3.5. Pendiente conocido (NO resuelto todavía)

`CitaForm` **no filtra** el desplegable de especialidad por `activa=True` —
hoy deja elegir especialidades inactivas al agendar una cita nueva. Se
identificó pero se decidió no tocarlo en esta sesión. Queda como tarea
pendiente (ver sección 5). El fix es de una línea:

```python
especialidad = forms.ModelChoiceField(
    queryset=Especialidad.objects.filter(activa=True),
    empty_label='Seleccione una especialidad',
)
```

---

## 4. Estado actual frente a la rúbrica

| Criterio | Estado | Detalle |
|---|---|---|
| % dominio implementado | Parcial | 2 entidades (`Cita`, `Especialidad`). Faltan `Medico` y `Paciente` como mínimo para acercarse al 50-60%. |
| SOLID y Service Layer | Bien encaminado | Sin lógica de negocio en `views.py` ni en `models.py`. Builder ya limpio de política hardcodeada. |
| DRF y API Gateway | No cumple | `rest_framework` no está instalado. No hay `serializers.py`. Las vistas siguen siendo HTML, no JSON. |
| Patrones Creacionales | Cumple | Builder y Factory correctamente resueltos y ya conectados a una entidad real de dominio. |
| Documentación (Wiki) | Pendiente | Este documento es la base, falta el diagrama de secuencia y la explicación de API Gateway que exige la rúbrica. |

---

## 5. Qué falta por hacer (roadmap para el equipo)

En orden recomendado — cada paso sigue el mismo patrón usado con
`Especialidad`: crear el modelo aislado primero, verificar que nada más se
rompe, y solo después conectar las relaciones con migraciones expand-contract
si hay datos existentes que migrar.

1. **Fix pendiente:** filtrar `CitaForm.especialidad` por `activa=True`
   (ver 3.5).
2. **Modelo `Medico`**: decidir si un médico tiene una sola especialidad
   (FK simple) o varias (relación muchos-a-muchos con `Especialidad`). Esta
   decisión hay que tomarla como equipo antes de escribir el modelo.
3. **Modelo `Paciente`**: la entidad más independiente, migración directa
   sin mucha complejidad relacional.
4. **Migrar `Cita.medico_nombre` y `Cita.paciente_nombre`** de `CharField` a
   `ForeignKey`, usando el mismo patrón expand-contract documentado en 3.3.
5. **Instalar y montar DRF**:
   - `pip install djangorestframework`, agregar a `INSTALLED_APPS`.
   - Crear `serializers.py` para entrada/salida de `Cita` (y las entidades
     nuevas).
   - Reescribir `AgendarCitaView` como `APIView` de DRF, manteniendo la
     llamada a `CitaService.agendar_cita()` intacta (el Service Layer ya
     está desacoplado de la vista, así que este paso es mecánico).
   - Mapear códigos HTTP: `201` al crear OK, `400` en validación de datos,
     `404` si el recurso no existe, `409` en conflicto de disponibilidad de
     horario (hoy ese caso lanza una `ValidationError` genérica en
     `services.py` — debe distinguirse de un `400`).
6. **Tests**: `citas/tests.py` está vacío. Agregar pruebas mínimas de
   `CitaService` y, después, de los endpoints DRF.
7. **`requirements.txt`**: no existe todavía en el repo.
8. **Wiki Técnica** (requisito explícito de entrega): justificar la
   estructura de carpetas, incluir un diagrama de secuencia del flujo más
   complejo (probablemente agendar cita), y explicar cómo el sistema está
   preparado para un API Gateway.

**Recordatorio para quien continúe:** no repitan el error original del
Builder — cualquier regla de negocio nueva (validaciones de horario, reglas
de `Medico`, etc.) va en `services.py` o como método/validación propia de la
entidad, nunca en `views.py` ni mezclada dentro de un Builder o Factory.

---

## 6. Archivos modificados/creados en esta sesión

- `citas/models.py` — nuevo modelo `Especialidad`; `Cita.especialidad` ahora
  es FK.
- `citas/builders.py` — eliminado el diccionario hardcodeado de políticas.
- `citas/admin.py` — `Especialidad` registrado.
- `citas/migrations/0004_especialidad.py` — crea la tabla `Especialidad`.
- `citas/migrations/0005_seed_especialidades.py` — siembra las 4
  especialidades iniciales (idempotente, con reversa).
- `citas/migrations/0006_cita_especialidad_fk.py` — expand.
- `citas/migrations/0007_backfill_especialidad_fk.py` — migrate data.
- `citas/migrations/0008_contract_especialidad_fk.py` — contract.
