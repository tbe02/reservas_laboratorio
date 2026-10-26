# reservas_laboratorio

Sistema local de reservas de equipos de laboratorio, construido con un agente de programación (Claude Code).

**Autor:** Theo Benjamín Echeverría
**Estado:** especificación inicial. El código todavía no existe; se construye por etapas (ver [PROGRESO.md](PROGRESO.md)).

El README tiene cuatro secciones:

1. [Especificación](#1-especificación)
2. [Solución](#2-solución)
3. [Preparación del agente](#3-preparación-del-agente)
4. [Registro de decisiones y delegación](#4-registro-de-decisiones-y-delegación)

---

## 1. Especificación

### 1.1 Problema

La coordinación de un laboratorio (contexto ficticio) registra los pedidos de equipos en mensajes y en una planilla. Esto provoca dos fallas:

- Se confirma la misma unidad para horarios superpuestos.
- Una reserva cancelada sigue bloqueando el horario.

Se necesita consultar disponibilidad, reservar y cancelar **sin perder el historial**.

### 1.2 Alcance

**Incluido**

- Leer el inventario precargado (5 unidades fijas).
- Consultar la disponibilidad de una unidad en un intervalo.
- Crear reservas identificables (una unidad por reserva).
- Cancelar reservas conservando sus datos y liberando el horario.
- Listar reservas activas y canceladas.
- Persistir reservas y estados entre ejecuciones.
- Inicializar o reiniciar la base de datos.

**Fuera de alcance**

Administración del inventario, modificación de reservas, reservas de varias unidades, autenticación y roles, notificaciones, pagos, integraciones externas, interfaz gráfica, despliegue y concurrencia distribuida.

### 1.3 Inventario

Cada ID identifica una unidad física distinta. El inventario se versiona en [`datos/inventario.csv`](datos/inventario.csv).

| ID | Equipo |
|---|---|
| MIC-01 | Microscopio digital |
| MIC-02 | Microscopio digital |
| OSC-01 | Osciloscopio |
| MUL-01 | Multímetro |
| FUE-01 | Fuente de alimentación |

### 1.4 Requisitos funcionales

| ID | Requisito |
|---|---|
| RF-01 | `unidades` muestra las 5 unidades del inventario. |
| RF-02 | `disponibilidad UNIDAD --desde FECHA --hasta FECHA` indica si la unidad está libre en el intervalo y, si no lo está, lista las reservas activas que la bloquean. Libre, ocupada o no reservable son resultados informativos (ver S-15). |
| RF-03 | `reservar UNIDAD --solicitante NOMBRE --inicio FECHA --fin FECHA` crea una reserva activa y devuelve su ID (`R-0001`, `R-0002`, …). |
| RF-04 | `cancelar ID` muestra la reserva, pide confirmación (s/n) y la marca como cancelada sin borrarla. |
| RF-05 | `listar [--unidad UNIDAD] [--estado activa\|cancelada]` muestra las reservas guardadas con las columnas ID, unidad, solicitante, inicio, fin y estado, ordenadas por inicio y luego por ID (ver S-16). |
| RF-06 | `inicializar` crea la base y carga el inventario. Si ya existen reservas, informa cuántas hay, advierte que se borrarán y pide confirmación (s/n). Si no hay reservas, crea o recrea la base sin preguntar e informa que se creó (ver S-13 y S-14). |
| RF-07 | Las reservas y sus estados se conservan al cerrar y volver a ejecutar la aplicación. |

### 1.5 Reglas de negocio

| ID | Regla |
|---|---|
| RN-01 | La unidad debe existir en el inventario. |
| RN-02 | El solicitante no puede estar vacío ni estar compuesto solo por espacios. |
| RN-03 | Las fechas deben ser válidas y respetar el formato `AAAA-MM-DD HH:MM`. |
| RN-04 | El inicio debe ser estrictamente anterior al fin. |
| RN-05 | El inicio de una reserva nueva debe ser posterior al momento actual. |
| RN-06 | Una reserva **activa** ocupa el intervalo `[inicio, fin)`. Una reserva **cancelada** no bloquea. |
| RN-07 | Dos reservas activas de la misma unidad se superponen si y solo si `inicio_A < fin_B` y `fin_A > inicio_B`. Las superposiciones se rechazan. |
| RN-08 | Los límites consecutivos están permitidos: 10:00–11:00 y 11:00–12:00 no se superponen. |
| RN-09 | Se permiten reservas simultáneas de unidades distintas. |
| RN-10 | La consulta de disponibilidad aplica las mismas reglas (RN-01, RN-03 a RN-07) que la creación, mediante la misma función. |
| RN-11 | Las reservas nunca se borran. Cancelar cambia el estado a `cancelada` y registra la fecha de cancelación. |
| RN-12 | Cancelar una reserva inexistente o ya cancelada produce un error y no modifica nada. |

**Ejemplo de la consigna:** con MIC-01 reservado de 10:00 a 11:00, se rechaza 10:30–11:30 y se permite 11:00–12:00. MIC-02 puede reservarse de 10:00 a 11:00 aunque MIC-01 esté ocupado.

### 1.6 Supuestos

| ID | Supuesto |
|---|---|
| S-01 | **Zona horaria:** todas las fechas se interpretan en hora de Buenos Aires (`America/Argentina/Buenos_Aires`, UTC-3, sin horario de verano). |
| S-02 | **Formato de fecha:** `AAAA-MM-DD HH:MM` (ej. `2030-11-03 10:00`), con precisión de minutos. |
| S-03 | **Fechas pasadas:** no se puede crear una reserva cuyo inicio sea igual o anterior al momento actual. Si en una consulta de disponibilidad el inicio ya pasó, se informa que el intervalo no es reservable. |
| S-04 | **El "ahora"** se toma de la hora real del sistema. El código lo recibe como parámetro opcional para que las pruebas usen una fecha fija; el usuario no puede modificarlo desde la CLI. |
| S-05 | **Duración y anticipación:** no hay límites. Una reserva puede cruzar la medianoche. |
| S-06 | **Normalización:** se recortan los espacios al inicio y al final del solicitante. El ID de unidad y el de reserva se aceptan sin distinguir mayúsculas (`mic-01` = `MIC-01`). |
| S-07 | **IDs de reserva:** se generan de forma consecutiva y nunca se reutilizan, ni siquiera los de reservas canceladas. Se muestran como `R-0001`. |
| S-08 | **Confirmaciones:** `inicializar` (si hay reservas) y `cancelar` piden confirmación. Se acepta `s`, `si`, `sí` como afirmativo; cualquier otra respuesta se toma como **no** y no se modifica nada. |
| S-09 | **Base no inicializada:** si la base no existe, los comandos distintos de `inicializar` muestran un error que indica ejecutar `inicializar`. |
| S-10 | **Códigos de salida:** 0 si la operación se completa; 1 si hay un error o el usuario no confirma. |
| S-11 | **Solicitantes:** se usan nombres ficticios; no se guardan datos reales. |
| S-12 | **Uso local de un solo usuario:** no se contempla concurrencia entre computadoras. La verificación y la inserción se hacen en una misma transacción. |
| S-13 | **Reinicio de la base:** `inicializar` borra el archivo de la base y lo crea de nuevo; no usa `DELETE` ni `DROP` sobre `reservas`. Después de reiniciar, los IDs vuelven a empezar en `R-0001`. S-07 aplica dentro de una misma base: mientras no se reinicie, nunca se reutiliza un ID. |
| S-14 | **Inicializar sin reservas:** si la base no existe, o existe pero no tiene reservas, `inicializar` la crea o la recrea sin pedir confirmación e informa que se creó. |
| S-15 | **Códigos de salida de `disponibilidad`:** devuelve 0 siempre que la consulta se complete, esté la unidad libre, ocupada o el intervalo no sea reservable por estar en el pasado; el resultado es información, no un error. Devuelve 1 solo si hay datos inválidos (unidad desconocida, fecha mal escrita, inicio igual o posterior al fin) o la base no está inicializada. |
| S-16 | **Salida de `listar`:** ordena por inicio ascendente y, si empatan, por ID. Columnas: ID, unidad, solicitante, inicio, fin, estado. Si no hay reservas, muestra `No hay reservas.` y devuelve 0. |
| S-17 | **Base sin tablas:** si el archivo de la base existe pero no tiene las tablas, se trata como base no inicializada (S-09). |

### 1.7 Criterios de aceptación

Cada criterio se verifica con una prueba automática, salvo indicación.

| ID | Criterio | Verificación |
|---|---|---|
| CA-01 | Tras `inicializar`, `unidades` lista exactamente las 5 unidades. | Automática |
| CA-02 | Una reserva válida se crea con estado `activa` y un ID nuevo. | Automática |
| CA-03 | Con MIC-01 reservado de 10:00 a 11:00, se rechaza 10:30–11:30. | Automática |
| CA-04 | Con MIC-01 reservado de 10:00 a 11:00, se permite 11:00–12:00. | Automática |
| CA-05 | Con MIC-01 reservado de 10:00 a 11:00, se permite MIC-02 de 10:00 a 11:00. | Automática |
| CA-06 | Se rechazan: unidad desconocida, solicitante vacío o solo espacios, formato de fecha inválido, fecha inexistente (ej. `2030-02-30`), inicio igual o posterior al fin, inicio en el pasado. | Automática |
| CA-07 | Al cancelar, la reserva conserva su ID y datos, pasa a `cancelada`, registra `cancelada_en` y el horario puede volver a reservarse. | Automática |
| CA-08 | Cancelar una reserva inexistente o ya cancelada da error y no cambia nada. | Automática |
| CA-09 | `disponibilidad` coincide con lo que aceptaría o rechazaría `reservar` en los casos CA-03 a CA-07. | Automática |
| CA-10 | Una reserva activa y una cancelada siguen existentes, con su estado, tras cerrar y volver a abrir la base. | Automática + procedimiento manual |
| CA-11 | Responder `n` a una confirmación no modifica la base. | Automática |
| CA-12 | Los comandos devuelven código 0 si salen bien y 1 si hay error. | Automática |
| CA-13 | Si la base no existe o no tiene reservas, `inicializar` la crea sin pedir confirmación. Si tiene reservas y se confirma, la recrea sin reservas y la siguiente reserva recibe el ID `R-0001`. | Automática |
| CA-14 | `disponibilidad` devuelve 0 con un intervalo libre, ocupado o en el pasado, y 1 con unidad desconocida, fecha mal escrita, inicio igual o posterior al fin o base no inicializada. | Automática |
| CA-15 | `listar` muestra las reservas ordenadas por inicio y luego por ID, con las columnas de S-16. Sin reservas, muestra `No hay reservas.` y devuelve 0. | Automática |
| CA-16 | Con un archivo de base existente pero sin tablas, los comandos distintos de `inicializar` muestran el error de base no inicializada y devuelven 1. | Automática |

### 1.8 Modelo de datos (SQLite)

```sql
CREATE TABLE unidades (
    id      TEXT PRIMARY KEY,                -- 'MIC-01'
    equipo  TEXT NOT NULL
);

CREATE TABLE reservas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,   -- se muestra como R-0001
    unidad_id     TEXT NOT NULL REFERENCES unidades(id),
    solicitante   TEXT NOT NULL CHECK (length(trim(solicitante)) > 0),
    inicio        TEXT NOT NULL,                       -- 'AAAA-MM-DD HH:MM'
    fin           TEXT NOT NULL,
    estado        TEXT NOT NULL DEFAULT 'activa'
                  CHECK (estado IN ('activa', 'cancelada')),
    creada_en     TEXT NOT NULL,                       -- 'AAAA-MM-DD HH:MM:SS'
    cancelada_en  TEXT,                                -- NULL mientras esté activa
    CHECK (inicio < fin)
);

CREATE INDEX idx_reservas_unidad_estado ON reservas (unidad_id, estado);
```

Consulta de superposición, compartida por `reservar` y `disponibilidad`:

```sql
SELECT * FROM reservas
WHERE unidad_id = :unidad
  AND estado = 'activa'
  AND inicio < :fin_nuevo
  AND fin > :inicio_nuevo;
```

### 1.9 Evolución de la especificación

La versión inicial de esta especificación es el primer commit del repositorio. Los cambios significativos se registran en [DECISIONES.md](DECISIONES.md) y quedan en el historial de Git.

---

## 2. Solución

> Pendiente: se completa a medida que se construye (etapa 7 de [PROGRESO.md](PROGRESO.md)). Solo se incluirán salidas de comandos realmente ejecutados.

Contenido previsto:

- **Estructura del proyecto.**
- **Requisitos previos:** Linux, Python 3.14.8 y las dependencias de `requirements.txt` (versiones fijas).
- **Instalación:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- **Carga inicial y reinicio de datos:** `python -m reservas inicializar`. ⚠️ Reiniciar **borra todas las reservas** (pide confirmación).
- **Dónde persisten los datos:** `datos/reservas.db` (excluido de Git). Se puede usar otra ruta con la variable de entorno `RESERVAS_DB`.
- **Comandos de la aplicación** con ejemplos de entrada y salida.
- **Pruebas:** `python -m pytest -v`.
- **Procedimiento manual de persistencia** con resultados esperados y observados.
- **Pendientes y limitaciones.**

---

## 3. Preparación del agente

### 3.1 Entorno y modelo

| Dato | Valor | Evidencia |
|---|---|---|
| Agente / harness | Claude Code (CLI en terminal, Linux) | — |
| Versión | 2.1.309 | Salida de `claude --version` |
| Modelo | Claude Opus 5.5 (`claude-opus-5-5`), esfuerzo alto | Salida de `/status` en [PROGRESO.md](PROGRESO.md#entorno-evidencia) |
| Plan | Claude Pro | — |

**Función:** el agente lee el repositorio, propone e implementa código y pruebas por etapas, y ejecuta pytest. Las ediciones y los commits requieren aprobación humana.

**Motivo de la elección:** Claude Code actúa sobre el repositorio con herramientas reales (lectura, edición, ejecución de comandos) y permite versionar sus instrucciones (`CLAUDE.md`) y permisos (`.claude/settings.json`). Se eligió el modelo de mayor capacidad con esfuerzo alto para priorizar la precisión en las reglas de borde (intervalos consecutivos, cancelaciones) sobre la velocidad.

**Reproducibilidad:** la aplicación y sus pruebas no dependen del agente ni de la cuenta del autor. Solo requieren Python y las dependencias de `requirements.txt`.

### 3.2 Instrucciones

- [`CLAUDE.md`](CLAUDE.md): instrucciones del proyecto. Claude Code lo lee automáticamente al iniciar en la carpeta del repositorio.
- Las instrucciones por tarea (prompts de cada etapa) se registran resumidas en [PROGRESO.md](PROGRESO.md).

### 3.3 Contexto suministrado y excluido

- **Suministrado:** este README (especificación), `CLAUDE.md`, `PROGRESO.md`, `DECISIONES.md` y el código del repositorio.
- **Excluido:** la consigna original completa (se tradujo a la especificación de este README), datos personales reales, credenciales y tokens, y la conversación de planificación previa.

### 3.4 Permisos y controles

Definidos en [`.claude/settings.json`](.claude/settings.json):

| Nivel | Acciones | Motivo |
|---|---|---|
| Permitido sin preguntar | Leer y buscar archivos; ejecutar pytest; `git status`, `git diff`, `git log` | Acciones sin efectos sobre el código |
| Requiere aprobación | Editar o crear archivos; ejecutar la aplicación; `git add`, `git commit`; instalar paquetes | El humano revisa cada cambio antes de aceptarlo |
| Prohibido | `git push`; `rm -rf`; leer archivos `.env` | La publicación la hace el humano; se evitan borrados y lectura de secretos |

**Revisión humana:** en cada etapa, el autor revisa el diff, ejecuta él mismo `python -m pytest -v` y decide si acepta, corrige o rechaza antes del commit. Ver [PROGRESO.md](PROGRESO.md).

### 3.5 Adaptaciones específicas

Instrucciones incluidas en `CLAUDE.md` para este problema:

1. **Regla de turnos consecutivos:** intervalos semiabiertos `[inicio, fin)` con comparación estricta, una sola función para reservar y consultar, y tests obligatorios del ejemplo de la consigna.
2. **Procedimiento de persistencia:** prohibido borrar reservas (`DELETE`); cancelar cambia el estado; test de cierre y reapertura de la base.
3. **El "ahora" como parámetro:** prohibido leer la hora desde variables de entorno.

Evidencia de uso:

- **Adaptación 1 (turnos consecutivos):** [prueba de mutación en PROGRESO.md](PROGRESO.md#prueba-de-mutación-turnos-consecutivos): con `<=`/`>=` en la consulta de superposición fallan 6 tests; sin el filtro de reservas activas falla 1. Tests de turnos consecutivos en [`tests/test_superposicion.py`](tests/test_superposicion.py): `test_consigna_permite_mic01_de_11_a_12`, `test_turno_consecutivo_anterior_se_permite` y `test_disponibilidad_coincide_con_crear_reserva` (casos consecutivos).
- **Adaptaciones 2 y 3:** pendiente, se enlazará en [PROGRESO.md](PROGRESO.md) a los commits y tests correspondientes.

### 3.6 Retención del progreso

[PROGRESO.md](PROGRESO.md) es un archivo versionado donde se registra el estado de cada etapa, las verificaciones ejecutadas y los episodios de delegación. `CLAUDE.md` indica al agente leerlo al iniciar y actualizarlo al terminar cada etapa.

---

## 4. Registro de decisiones y delegación

- **Decisiones técnicas:** [DECISIONES.md](DECISIONES.md).
- **Episodios de delegación:** [PROGRESO.md › Episodios](PROGRESO.md#episodios-de-delegación). Pendiente: se registran durante la construcción.
