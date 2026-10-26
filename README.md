# reservas_laboratorio

Sistema local de reservas de equipos de laboratorio, construido con un agente de programación (Claude Code).

**Autor:** Theo Benjamín Echeverría
**Estado:** aplicación completa según la especificación (§1): CLI con los 6 comandos, 165 pruebas automáticas y procedimiento manual de persistencia ejecutado por el autor. Construida por etapas, con historial y verificaciones en [PROGRESO.md](PROGRESO.md).

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
| RF-02 | `disponibilidad UNIDAD --desde FECHA --hasta FECHA` indica si la unidad está libre en el intervalo y, si no lo está, lista las reservas activas que la bloquean. Libre, ocupada o no reservable son resultados informativos (ver S-15 y S-18). |
| RF-03 | `reservar UNIDAD --solicitante NOMBRE --inicio FECHA --fin FECHA` crea una reserva activa y devuelve su ID (`R-0001`, `R-0002`, …). |
| RF-04 | `cancelar ID` muestra la reserva, pide confirmación (s/n) y la marca como cancelada sin borrarla. Solo se pueden cancelar reservas que todavía no empezaron (ver S-19). |
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
| S-18 | **Disponibilidad en el pasado y ocupada:** si el inicio del intervalo ya pasó y además hay reservas activas que se superponen, `disponibilidad` informa las dos cosas: que el intervalo no es reservable por estar en el pasado y las reservas que lo bloquean. Devuelve 0 (S-15). |
| S-19 | **Cancelar una reserva que ya empezó:** si el inicio de la reserva es igual o anterior al momento actual (en curso o terminada), `cancelar` produce un error y no modifica nada. |

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
| CA-17 | Con un intervalo en el pasado que además se superpone con una reserva activa, `disponibilidad` informa que no es reservable, lista la reserva que lo bloquea y devuelve 0. | Automática |
| CA-18 | Cancelar una reserva cuyo inicio es igual o anterior al momento actual da error y no cambia nada; una reserva que todavía no empezó se cancela normalmente. | Automática |

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

Todas las salidas de esta sección son de comandos realmente ejecutados el 2026-10-26. Los ejemplos de [2.7](#27-comandos) salen de una corrida contra `/tmp/reservas_readme.db`, y los del [procedimiento manual](#29-procedimiento-manual-de-persistencia-ca-10), de las corridas del agente y del autor.

### 2.1 Estructura del proyecto

```
reservas_laboratorio/
├── README.md                 especificación (§1), solución (§2) y preparación del agente (§3)
├── CLAUDE.md                 instrucciones del proyecto para el agente
├── PROGRESO.md               etapas, bitácora, verificaciones y episodios de delegación
├── DECISIONES.md             registro de decisiones técnicas (D-01 a D-30)
├── requirements.txt          dependencia única con versión fija: pytest==9.1.1
├── .gitignore                excluye la base de datos, el entorno virtual y los secretos
├── .claude/settings.json     permisos del agente (permitido, requiere aprobación, prohibido)
├── datos/
│   ├── inventario.csv        las 5 unidades del inventario (versionado)
│   └── reservas.db           base SQLite; la crea `inicializar` (no se versiona)
├── reservas/                 paquete de la aplicación
│   ├── __init__.py           marca el paquete
│   ├── __main__.py           punto de entrada de `python -m reservas`
│   ├── cli.py                capa CLI: argumentos, confirmaciones, salida y códigos de salida
│   ├── reglas.py             capa de reglas de negocio: validaciones, disponibilidad, reservar, cancelar, listar
│   ├── persistencia.py       capa de persistencia: esquema SQLite, consultas y transacciones
│   └── errores.py            excepciones con mensajes en español para el usuario
└── tests/
    ├── conftest.py           base temporal por test (`tmp_path`)
    ├── test_persistencia.py  esquema, inventario, base no inicializada, cierre y reapertura
    ├── test_crear_reserva.py validaciones de RN-01 a RN-05
    ├── test_superposicion.py superposición, turnos consecutivos, disponibilidad y transacción
    ├── test_cancelar_reserva.py  cancelación sin borrar, errores y reservas ya empezadas
    └── test_cli.py           los 6 comandos, confirmaciones, códigos de salida y 2 pruebas de punta a punta
```

**Capas.** La CLI no contiene reglas de negocio: solo interpreta los argumentos, pide confirmaciones y muestra resultados.

- **CLI** (`cli.py`) llama a las reglas.
- **Reglas** (`reglas.py`) validan los datos y deciden qué se puede hacer.
- **Persistencia** (`persistencia.py`) accede a SQLite.

La detección de superposición es una sola consulta (`persistencia.buscar_conflictos`), que usan tanto `reservar` como `disponibilidad` a través de `reglas.consultar_disponibilidad`.

### 2.2 Decisiones técnicas (resumen)

El detalle, con alternativas y consecuencias, está en [DECISIONES.md](DECISIONES.md).

| Tema | Decisión | Ref. |
|---|---|---|
| Lenguaje, interfaz y datos | Python 3.14 + pytest; CLI con `argparse`; SQLite (`sqlite3` de la biblioteca estándar) | D-01 a D-03 |
| Superposición | Intervalos `[inicio, fin)` con comparación estricta; una sola función para reservar y consultar | D-04, D-05 |
| Fechas | Hora de Buenos Aires, formato `AAAA-MM-DD HH:MM`, guardadas como texto; no se recortan espacios | D-06, D-23 |
| El "ahora" | No se reserva en el pasado; el "ahora" es un parámetro de las funciones, nunca una variable de entorno ni un argumento | D-07, D-08, D-22 |
| Historial | Cancelar es `UPDATE`, nunca `DELETE`; no se cancelan reservas ya empezadas | D-10, D-26 |
| IDs | Enteros consecutivos mostrados como `R-0001`; `R-1` es la misma reserva | D-11, D-25 |
| Confirmaciones | Solo en `inicializar` (si hay reservas) y `cancelar`; mayúsculas y espacios no importan; sin entrada es "no" | D-12, D-17, D-28 |
| Transacciones | Verificar e insertar dentro de `BEGIN IMMEDIATE` | D-13 |
| Reinicio | `inicializar` borra el archivo de la base y los IDs vuelven a `R-0001` | D-16 |
| Rutas | Ruta por defecto relativa a la raíz del proyecto; otra ruta con `RESERVAS_DB` | D-03, D-21 |
| CLI | Código de salida 0/1, también para errores de argumentos; `disponibilidad` devuelve 0 si la consulta se completa; `cancelar` valida antes de preguntar | D-14, D-18, D-29, D-30 |
| Salida | `listar` ordena por inicio y luego por ID; en el pasado y ocupado se informan ambas cosas | D-19, D-24, D-27 |

### 2.3 Requisitos previos

| Requisito | Versión usada | Comprobación |
|---|---|---|
| Sistema operativo | Linux | — |
| Python | 3.14.8 | `python3 --version` → `Python 3.14.8` |
| pytest (única dependencia) | 9.1.1 (fija en `requirements.txt`) | `.venv/bin/python -m pytest --version` → `pytest 9.1.1` |
| Base de datos de zonas horarias del sistema | la del sistema operativo | `ls /usr/share/zoneinfo/America/Argentina/Buenos_Aires` (la usa `zoneinfo`) |

pip instala además las dependencias de pytest (`iniconfig`, `packaging`, `pluggy`, `pygments`). Esas no tienen versión fija en `requirements.txt`.

### 2.4 Instalación desde cero

```bash
git clone https://github.com/tbe02/reservas_laboratorio.git
cd reservas_laboratorio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Con el entorno activado, `python -m reservas …` equivale a `.venv/bin/python -m reservas …`. Los ejemplos de esta sección usan la forma explícita, que funciona aunque el entorno no esté activado.

Estos pasos se verificaron clonando el repositorio local en una carpeta nueva (commit `55fe6df`): `git clone`, `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt` (`Successfully installed iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1`) y `.venv/bin/python -m pytest -v` → `165 passed in 2.00s`. pip tomó los paquetes de su caché local, así que la descarga desde la red no se verificó en esa prueba.

### 2.5 Carga inicial y reinicio de datos

```bash
.venv/bin/python -m reservas inicializar
```

Crea la base y carga las 5 unidades de `datos/inventario.csv`. Si la base no existe o no tiene reservas, la crea sin preguntar:

```
Base de datos creada en /tmp/reservas_readme.db con las unidades del inventario.
```

> ⚠️ **Reiniciar BORRA TODAS LAS RESERVAS.** Si la base ya tiene reservas, `inicializar` informa cuántas hay y pide confirmación. Solo `s`, `si` o `sí` confirman; cualquier otra respuesta cancela y no modifica nada. Al confirmar, se borra el archivo de la base, se crea de nuevo y los IDs vuelven a empezar en `R-0001`. Esto no se puede deshacer.

```
$ echo n | .venv/bin/python -m reservas inicializar
La base tiene 3 reservas. Si continuás, se borrarán todas.
¿Reiniciar la base? (s/n): Operación cancelada. No se modificó la base.
código: 1
```

En los ejemplos con `echo n |` o `echo s |`, la respuesta llega por la entrada estándar y por eso no aparece escrita después de la pregunta. En una terminal interactiva se escribe a mano.

Si se ejecuta cualquier otro comando sin haber inicializado la base, aparece:

```
Error: La base de datos no está inicializada. Ejecutá: python -m reservas inicializar
código: 1
```

### 2.6 Dónde persisten los datos

- **Por defecto:** en `datos/reservas.db`, dentro del repositorio. La ruta se calcula desde la carpeta que contiene `reservas/`, no desde la carpeta actual (D-21). El archivo está excluido de Git en `.gitignore` (`datos/*.db` y sus archivos auxiliares `-journal`, `-wal`, `-shm`).
- **Otra ruta:** con la variable de entorno `RESERVAS_DB`, por ejemplo para pruebas que no deben tocar la base real:

  ```bash
  export RESERVAS_DB=/tmp/mi_prueba.db
  .venv/bin/python -m reservas inicializar
  ```

  Si `RESERVAS_DB` es una ruta relativa, se toma desde la carpeta actual.

### 2.7 Comandos

Los 6 comandos, con un ejemplo de entrada y salida cada uno. Se ejecutaron en este orden con `export RESERVAS_DB=/tmp/reservas_readme.db`, y después de cada comando se mostró el código de salida con `echo "código: $?"`. Las fechas son de 2099 porque no se puede reservar en el pasado; el ejemplo de "no reservable" usa a propósito una fecha de 2020.

```
$ .venv/bin/python -m reservas --help
uso: python -m reservas [-h] COMANDO ...

Reservas de equipos de laboratorio.

opciones:
  -h, --help        muestra esta ayuda y termina

comandos:
  COMANDO
    inicializar     crea la base y carga el inventario (borra las reservas)
    unidades        muestra las unidades del inventario
    disponibilidad  indica si una unidad está libre en un intervalo
    reservar        crea una reserva
    cancelar        cancela una reserva
    listar          muestra las reservas guardadas
código: 0
```

**`inicializar`:** ver [2.5](#25-carga-inicial-y-reinicio-de-datos).

**`unidades`:** muestra las 5 unidades del inventario.

```
$ .venv/bin/python -m reservas unidades
ID      Equipo
MIC-01  Microscopio digital
MIC-02  Microscopio digital
OSC-01  Osciloscopio
MUL-01  Multímetro
FUE-01  Fuente de alimentación
código: 0
```

**`reservar UNIDAD --solicitante NOMBRE --inicio FECHA --fin FECHA`:** crea una reserva activa y muestra su ID. Las fechas van entre comillas porque tienen un espacio.

```
$ .venv/bin/python -m reservas reservar MIC-01 --solicitante "Ana Prueba" --inicio "2099-11-03 10:00" --fin "2099-11-03 11:00"
Reserva creada: R-0001 (MIC-01, 2099-11-03 10:00 a 2099-11-03 11:00, Ana Prueba).
código: 0

$ .venv/bin/python -m reservas reservar MIC-01 --solicitante "Beto Prueba" --inicio "2099-11-03 10:30" --fin "2099-11-03 11:30"
Error: La unidad MIC-01 ya está reservada en ese horario: R-0001 (2099-11-03 10:00 a 2099-11-03 11:00).
código: 1

$ .venv/bin/python -m reservas reservar MIC-01 --solicitante "Beto Prueba" --inicio "2099-11-03 11:00" --fin "2099-11-03 12:00"
Reserva creada: R-0002 (MIC-01, 2099-11-03 11:00 a 2099-11-03 12:00, Beto Prueba).
código: 0

$ .venv/bin/python -m reservas reservar MIC-02 --solicitante "Caro Prueba" --inicio "2099-11-03 10:00" --fin "2099-11-03 11:00"
Reserva creada: R-0003 (MIC-02, 2099-11-03 10:00 a 2099-11-03 11:00, Caro Prueba).
código: 0

$ .venv/bin/python -m reservas reservar MIC-01 --solicitante "Ana Prueba" --inicio "2099-02-30 10:00" --fin "2099-02-30 11:00"
Error: La fecha de inicio '2099-02-30 10:00' no es una fecha válida.
código: 1
```

Es el ejemplo de la consigna con fechas de 2099: 10:30–11:30 choca con R-0001; 11:00–12:00 es un turno consecutivo y se permite; MIC-02 se puede reservar en el mismo horario que MIC-01.

**`disponibilidad UNIDAD --desde FECHA --hasta FECHA`:** indica si la unidad está libre y, si no lo está, lista las reservas que la bloquean. Devuelve 0 siempre que la consulta se complete (S-15).

```
$ .venv/bin/python -m reservas disponibilidad MIC-01 --desde "2099-11-03 10:30" --hasta "2099-11-03 11:30"
La unidad MIC-01 está ocupada del 2099-11-03 10:30 al 2099-11-03 11:30. Reservas que la bloquean:
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0001  MIC-01  Ana Prueba   2099-11-03 10:00  2099-11-03 11:00  activa
R-0002  MIC-01  Beto Prueba  2099-11-03 11:00  2099-11-03 12:00  activa
código: 0

$ .venv/bin/python -m reservas disponibilidad MIC-01 --desde "2099-11-03 12:00" --hasta "2099-11-03 13:00"
La unidad MIC-01 está libre del 2099-11-03 12:00 al 2099-11-03 13:00.
código: 0

$ .venv/bin/python -m reservas disponibilidad MIC-01 --desde "2020-01-01 10:00" --hasta "2020-01-01 11:00"
El intervalo del 2020-01-01 10:00 al 2020-01-01 11:00 no es reservable: el inicio ya pasó.
código: 0
```

**`cancelar ID`:** muestra la reserva, pide confirmación y la marca como cancelada sin borrarla.

```
$ echo n | .venv/bin/python -m reservas cancelar R-0003
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0003  MIC-02  Caro Prueba  2099-11-03 10:00  2099-11-03 11:00  activa
¿Cancelar la reserva R-0003? (s/n): Operación cancelada. No se modificó la reserva.
código: 1

$ echo s | .venv/bin/python -m reservas cancelar R-0003
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0003  MIC-02  Caro Prueba  2099-11-03 10:00  2099-11-03 11:00  activa
¿Cancelar la reserva R-0003? (s/n): Reserva R-0003 cancelada.
código: 0

$ .venv/bin/python -m reservas cancelar R-0003
Error: La reserva R-0003 ya está cancelada (desde 2026-10-26 19:50:04).
código: 1
```

`cancelada_en` registra la hora real de Buenos Aires del momento de la cancelación.

**`listar [--unidad UNIDAD] [--estado activa|cancelada]`:** muestra las reservas ordenadas por inicio y luego por ID (por eso R-0003 aparece antes que R-0002). Si no hay reservas, muestra `No hay reservas.`

```
$ .venv/bin/python -m reservas listar
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0001  MIC-01  Ana Prueba   2099-11-03 10:00  2099-11-03 11:00  activa
R-0003  MIC-02  Caro Prueba  2099-11-03 10:00  2099-11-03 11:00  cancelada
R-0002  MIC-01  Beto Prueba  2099-11-03 11:00  2099-11-03 12:00  activa
código: 0

$ .venv/bin/python -m reservas listar --unidad mic-01 --estado activa
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0001  MIC-01  Ana Prueba   2099-11-03 10:00  2099-11-03 11:00  activa
R-0002  MIC-01  Beto Prueba  2099-11-03 11:00  2099-11-03 12:00  activa
código: 0

$ .venv/bin/python -m reservas listar --estado pendiente
uso: python -m reservas listar [-h] [--unidad UNIDAD]
                               [--estado {activa,cancelada}]
Error: argumento --estado: opción inválida: 'pendiente' (opciones válidas 'activa', 'cancelada')
código: 1
```

**Códigos de salida:** 0 si la operación se completa; 1 si hay un error o no se confirma (S-10).

### 2.8 Pruebas

```bash
.venv/bin/python -m pytest -v
```

Hay **165 pruebas automáticas**. Cada una usa una base temporal (`tmp_path`), nunca `datos/reservas.db`. Última corrida del agente sobre el código de la etapa 6: `165 passed in 1.85s`.

| Archivo | Pruebas | Qué cubre |
|---|---|---|
| `tests/test_persistencia.py` | 10 | esquema e inventario (CA-01), base inexistente o sin tablas, `RESERVAS_DB`, cierre y reapertura (CA-10) |
| `tests/test_crear_reserva.py` | 48 | creación válida (CA-02) y cada caso inválido de CA-06; dos con hora real y fechas de 2000 y 2099 |
| `tests/test_superposicion.py` | 33 | ejemplo de la consigna (CA-03 a CA-05), superposiciones, disponibilidad igual a reservar (CA-09), `BEGIN IMMEDIATE` |
| `tests/test_cancelar_reserva.py` | 21 | cancelación sin borrar (CA-07), errores (CA-08), reservas ya empezadas (CA-18), `UPDATE` sin `DELETE` |
| `tests/test_cli.py` | 53 | los 6 comandos, confirmaciones (CA-11), códigos de salida (CA-12) y CA-13 a CA-17; 2 de punta a punta con `python -m reservas` en otro proceso |

Las pruebas con `ahora` fijo usan fechas de 2030. Las que usan la hora real (camino `ahora=None` y punta a punta) usan 2099, para que sigan siendo futuras.

### 2.9 Procedimiento manual de persistencia (CA-10)

Comprueba que una reserva activa y una cancelada se conservan, con su estado, al cerrar la aplicación y la terminal y volver a ejecutarla (RF-07). Complementa el test automático `tests/test_persistencia.py::test_reserva_activa_y_cancelada_persisten_al_cerrar_y_reabrir`.

- La base se crea en `/tmp/reservas_persistencia.db` mediante `RESERVAS_DB`, así que **no se toca `datos/reservas.db`**.
- Las fechas son de 2099 porque la aplicación usa la hora real y no se puede reservar en el pasado.
- Cada comando va seguido de `; echo "código: $?"`, que muestra su código de salida.

**Sesión 1** (desde la carpeta del repositorio, con las dependencias instaladas):

```bash
ls /tmp/reservas_persistencia.db; echo "código: $?"
export RESERVAS_DB=/tmp/reservas_persistencia.db
.venv/bin/python -m reservas inicializar; echo "código: $?"
.venv/bin/python -m reservas reservar MIC-01 --solicitante "Ana Prueba" --inicio "2099-11-03 10:00" --fin "2099-11-03 11:00"; echo "código: $?"
.venv/bin/python -m reservas reservar MIC-02 --solicitante "Beto Prueba" --inicio "2099-11-03 10:00" --fin "2099-11-03 11:00"; echo "código: $?"
.venv/bin/python -m reservas cancelar R-0002; echo "código: $?"
.venv/bin/python -m reservas listar; echo "código: $?"
```

**Reinicio:** cerrar la terminal, abrir una nueva y volver a la carpeta del repositorio.

**Sesión 2:**

```bash
export RESERVAS_DB=/tmp/reservas_persistencia.db
.venv/bin/python -m reservas listar; echo "código: $?"
.venv/bin/python -m reservas disponibilidad MIC-01 --desde "2099-11-03 10:00" --hasta "2099-11-03 11:00"; echo "código: $?"
.venv/bin/python -m reservas disponibilidad MIC-02 --desde "2099-11-03 10:00" --hasta "2099-11-03 11:00"; echo "código: $?"
.venv/bin/python -m reservas reservar MIC-02 --solicitante "Caro Prueba" --inicio "2099-11-03 10:00" --fin "2099-11-03 11:00"; echo "código: $?"
.venv/bin/python -m reservas listar; echo "código: $?"
ls datos/
```

| Paso | Comando | Resultado esperado | Resultado observado |
|---|---|---|---|
| 1 | `ls /tmp/reservas_persistencia.db` | El archivo no existe. Si existe, `inicializar` va a preguntar si se borran sus reservas: responder `s`. | `ls: no se puede acceder a '/tmp/reservas_persistencia.db': No existe el fichero o el directorio` (código 2, de `ls`). Coincide. |
| 2 | `inicializar` | `Base de datos creada en /tmp/reservas_persistencia.db con las unidades del inventario.` Código 0. | Mismo mensaje. Código 0. Coincide. |
| 3 | `reservar MIC-01 … Ana Prueba` | `Reserva creada: R-0001 (MIC-01, 2099-11-03 10:00 a 2099-11-03 11:00, Ana Prueba).` Código 0. | Mismo mensaje. Código 0. Coincide. |
| 4 | `reservar MIC-02 … Beto Prueba` | `Reserva creada: R-0002 (MIC-02, 2099-11-03 10:00 a 2099-11-03 11:00, Beto Prueba).` Código 0. | Mismo mensaje. Código 0. Coincide. |
| 5 | `cancelar R-0002`, responder `s` | Muestra R-0002 (MIC-02, Beto Prueba, `activa`), pregunta `¿Cancelar la reserva R-0002? (s/n):` y, tras `s`, `Reserva R-0002 cancelada.` Código 0. | Mostró R-0002 `activa`, `¿Cancelar la reserva R-0002? (s/n): s` y `Reserva R-0002 cancelada.` Código 0. Coincide. |
| 6 | `listar` | R-0001 `activa` y R-0002 `cancelada`. Código 0. | R-0001 `activa` y R-0002 `cancelada`. Código 0. Coincide. |
| 7 | Cerrar la terminal y abrir una nueva | — | El autor reinició la terminal. |
| 8 | `listar` | Igual que en el paso 6: R-0001 `activa` y R-0002 `cancelada`. Código 0. | R-0001 `activa` y R-0002 `cancelada`. Código 0. Coincide. |
| 9 | `disponibilidad MIC-01 …` | `La unidad MIC-01 está ocupada del 2099-11-03 10:00 al 2099-11-03 11:00.` y la tabla con R-0001. Código 0. | Mismo mensaje y tabla con R-0001. Código 0. Coincide. |
| 10 | `disponibilidad MIC-02 …` | `La unidad MIC-02 está libre del 2099-11-03 10:00 al 2099-11-03 11:00.` (la cancelada no bloquea). Código 0. | Mismo mensaje. Código 0. Coincide. |
| 11 | `reservar MIC-02 … Caro Prueba` | `Reserva creada: R-0003 (…)`: el ID de la cancelada no se reutiliza. Código 0. | `Reserva creada: R-0003 (MIC-02, 2099-11-03 10:00 a 2099-11-03 11:00, Caro Prueba).` Código 0. Coincide. |
| 12 | `listar` | R-0001 `activa`, R-0002 `cancelada` y R-0003 `activa`. Código 0. | R-0001 `activa`, R-0002 `cancelada` y R-0003 `activa`. Código 0. Coincide. |
| 13 | `ls datos/` | Solo `inventario.csv`: no se creó `datos/reservas.db`. | `inventario.csv`. Coincide. |

Resultados observados: ejecución del autor, 2026-10-26, en dos sesiones de terminal separadas por un reinicio. Los 13 pasos coincidieron con lo esperado.

Para borrar la base de prueba al terminar: `rm /tmp/reservas_persistencia.db`.

<details>
<summary>Salida obtenida por el agente al preparar el procedimiento (2026-10-26, con <code>RESERVAS_DB=/tmp/reservas_persistencia_agente.db</code>)</summary>

Se ejecutaron los mismos comandos en dos shells distintos, con otra ruta para no dejar creada la base del procedimiento. En el paso 5 la respuesta `s` se pasó por la entrada estándar (`echo s | …`), por eso no aparece escrita después de la pregunta.

Sesión 1:

```
Base de datos creada en /tmp/reservas_persistencia_agente.db con las unidades del inventario.
[código de salida: 0]
Reserva creada: R-0001 (MIC-01, 2099-11-03 10:00 a 2099-11-03 11:00, Ana Prueba).
[código de salida: 0]
Reserva creada: R-0002 (MIC-02, 2099-11-03 10:00 a 2099-11-03 11:00, Beto Prueba).
[código de salida: 0]
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0002  MIC-02  Beto Prueba  2099-11-03 10:00  2099-11-03 11:00  activa
¿Cancelar la reserva R-0002? (s/n): Reserva R-0002 cancelada.
[código de salida: 0]
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0001  MIC-01  Ana Prueba   2099-11-03 10:00  2099-11-03 11:00  activa
R-0002  MIC-02  Beto Prueba  2099-11-03 10:00  2099-11-03 11:00  cancelada
[código de salida: 0]
```

Sesión 2 (shell nuevo, `RESERVAS_DB` vacía antes del `export`):

```
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0001  MIC-01  Ana Prueba   2099-11-03 10:00  2099-11-03 11:00  activa
R-0002  MIC-02  Beto Prueba  2099-11-03 10:00  2099-11-03 11:00  cancelada
[código de salida: 0]
La unidad MIC-01 está ocupada del 2099-11-03 10:00 al 2099-11-03 11:00. Reservas que la bloquean:
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0001  MIC-01  Ana Prueba   2099-11-03 10:00  2099-11-03 11:00  activa
[código de salida: 0]
La unidad MIC-02 está libre del 2099-11-03 10:00 al 2099-11-03 11:00.
[código de salida: 0]
Reserva creada: R-0003 (MIC-02, 2099-11-03 10:00 a 2099-11-03 11:00, Caro Prueba).
[código de salida: 0]
ID      Unidad  Solicitante  Inicio            Fin               Estado
R-0001  MIC-01  Ana Prueba   2099-11-03 10:00  2099-11-03 11:00  activa
R-0002  MIC-02  Beto Prueba  2099-11-03 10:00  2099-11-03 11:00  cancelada
R-0003  MIC-02  Caro Prueba  2099-11-03 10:00  2099-11-03 11:00  activa
[código de salida: 0]
inventario.csv
```

</details>

### 2.10 Pendientes y limitaciones

**Pendientes:** no quedan funcionalidades pendientes de la especificación (§1). El estado de cada etapa y las verificaciones están en [PROGRESO.md](PROGRESO.md).

**Limitaciones de la aplicación:**

- **Zona horaria única:** todas las fechas se interpretan en hora de Buenos Aires (S-01, D-06). No se pueden ingresar fechas de otra zona horaria.
- **Depende del reloj del sistema:** el "ahora" se toma de la hora del sistema y no se puede fijar desde la CLI (D-08). Si el reloj está mal, las reglas de fechas pasadas se aplican con esa hora.
- **Depende de la base de zonas horarias del sistema:** `zoneinfo` usa la del sistema operativo (en Linux, `/usr/share/zoneinfo`). Sin ella, la aplicación no puede calcular la hora de Buenos Aires. El paquete `tzdata` no está en `requirements.txt` y el caso no se probó.
- **Sin modificar reservas** (fuera de alcance, §1.2): para cambiar una reserva hay que cancelarla y crear otra. Solo se pueden cancelar reservas que todavía no empezaron (S-19).
- **Sin concurrencia distribuida:** está pensada para un solo usuario local. `BEGIN IMMEDIATE` evita superposiciones entre procesos de la misma computadora, pero no entre computadoras (S-12, D-13).
- **Reiniciar borra todo y reutiliza IDs:** después de `inicializar`, `R-0001` puede referirse a una reserva distinta de la de antes del reinicio (D-16).
- **Sin límites de duración ni anticipación:** una reserva puede bloquear una unidad por un período muy largo (D-09).
- **Formato de fecha estricto:** `AAAA-MM-DD HH:MM` con ceros a la izquierda y sin espacios extra (D-23).
- **Mensajes de argparse traducidos en parte:** los errores de argumentos más comunes están en español; otros mensajes internos de argparse pueden aparecer en inglés (D-30).
- **Confirmaciones por pipe:** si la respuesta llega por la entrada estándar (`echo s | …`), no se ve escrita después de la pregunta y el mensaje siguiente queda en la misma línea.
- **Dependencias no fijadas:** solo pytest tiene versión fija; sus dependencias toman la última versión compatible al instalar.

**Limitaciones del proceso con el agente** (detalle en [PROGRESO.md › Entorno](PROGRESO.md#entorno-evidencia)): las reglas de permisos por prefijo de `.claude/settings.json` no cubren comandos armados con variables o funciones de shell, y no se pudo confirmar si dos ejecuciones del agente (la instalación de pytest en la etapa 1 y la prueba manual de la etapa 5) pidieron aprobación.

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
| Permitido sin preguntar | Leer y buscar archivos; ejecutar pytest (`python -m pytest`, `pytest` y `.venv/bin/python -m pytest`); `git status`, `git diff`, `git log` | Acciones sin efectos sobre el código |
| Requiere aprobación | Editar o crear archivos; ejecutar la aplicación (`python -m reservas` y `.venv/bin/python -m reservas`); `git add`, `git commit`; instalar paquetes | El humano revisa cada cambio antes de aceptarlo |
| Prohibido | `git push`; `rm -rf`; leer archivos `.env` | La publicación la hace el humano; se evitan borrados y lectura de secretos |

**Modo de inicio:** `"defaultMode": "default"` hace que Claude Code arranque en modo manual en este proyecto. No impide cambiar de modo durante la sesión, y lo puede reemplazar una configuración de mayor prioridad (por ejemplo, `.claude/settings.local.json` o un modo indicado al iniciar Claude Code). Las reglas ask siguen vigentes aunque cambie el modo: en el [incidente de permisos](PROGRESO.md#entorno-evidencia), la regla de `git commit` pidió aprobación con el modo automático activo.

**Revisión humana:** en cada etapa, el autor revisa el diff, ejecuta él mismo `python -m pytest -v` y decide si acepta, corrige o rechaza antes del commit. Ver [PROGRESO.md](PROGRESO.md).

### 3.5 Adaptaciones específicas

Instrucciones incluidas en `CLAUDE.md` para este problema:

1. **Regla de turnos consecutivos:** intervalos semiabiertos `[inicio, fin)` con comparación estricta, una sola función para reservar y consultar, y tests obligatorios del ejemplo de la consigna.
2. **Procedimiento de persistencia:** prohibido borrar reservas (`DELETE`); cancelar cambia el estado; test de cierre y reapertura de la base.
3. **El "ahora" como parámetro:** prohibido leer la hora desde variables de entorno.

Evidencia de uso:

- **Adaptación 1 (turnos consecutivos):** [prueba de mutación en PROGRESO.md](PROGRESO.md#prueba-de-mutación-turnos-consecutivos): con `<=`/`>=` en la consulta de superposición fallan 6 tests; sin el filtro de reservas activas falla 1. Tests de turnos consecutivos en [`tests/test_superposicion.py`](tests/test_superposicion.py): `test_consigna_permite_mic01_de_11_a_12`, `test_turno_consecutivo_anterior_se_permite` y `test_disponibilidad_coincide_con_crear_reserva` (casos consecutivos).
- **Adaptación 2 (persistencia):** la cancelación ejecuta `UPDATE` y ningún `DELETE` dentro de `BEGIN IMMEDIATE` … `COMMIT` (test `test_cancelar_usa_update_y_nunca_delete` en [`tests/test_cancelar_reserva.py`](tests/test_cancelar_reserva.py)); el autor verificó con `grep -rn -i "delete" reservas/` que `DELETE` solo aparece en un docstring ([Verificaciones ejecutadas en PROGRESO.md](PROGRESO.md#verificaciones-ejecutadas), etapa 4). Una reserva activa y una cancelada siguen con su estado tras cerrar y reabrir la base (test `test_reserva_activa_y_cancelada_persisten_al_cerrar_y_reabrir` en [`tests/test_persistencia.py`](tests/test_persistencia.py)) y tras reiniciar la terminal ([procedimiento manual de persistencia](#29-procedimiento-manual-de-persistencia-ca-10), ejecutado por el autor).
- **Adaptación 3 (el "ahora" como parámetro):** el autor verificó con `grep -rn "environ" reservas/` que la única variable de entorno que se lee es `RESERVAS_DB` ([Verificaciones ejecutadas en PROGRESO.md](PROGRESO.md#verificaciones-ejecutadas), etapa 2). Tests del camino `ahora=None` en [`tests/test_crear_reserva.py`](tests/test_crear_reserva.py): `test_ahora_none_acepta_una_reserva_en_2099` y `test_ahora_none_rechaza_una_reserva_en_2000`.

### 3.6 Retención del progreso

[PROGRESO.md](PROGRESO.md) es un archivo versionado donde se registra el estado de cada etapa, las verificaciones ejecutadas y los episodios de delegación. `CLAUDE.md` indica al agente leerlo al iniciar y actualizarlo al terminar cada etapa.

---

## 4. Registro de decisiones y delegación

### 4.1 Decisiones más importantes

El registro completo (D-01 a D-30), con contexto, alternativas y consecuencias, está en [DECISIONES.md](DECISIONES.md). D-01 a D-15 se tomaron en la planificación; D-16 en adelante surgieron durante la construcción, propuestas o planteadas por el agente y decididas por el autor.

- **Intervalos semiabiertos con comparación estricta y una sola función de conflictos** (D-04, D-05): los turnos consecutivos no chocan y `disponibilidad` coincide siempre con `reservar`.
- **El "ahora" como parámetro, no como variable de entorno** (D-08): se descartó la variable `RESERVAS_AHORA` porque permitía saltear la regla de fechas pasadas.
- **Cancelar sin borrar** (D-10): `UPDATE` del estado y `cancelada_en`; nunca `DELETE`.
- **Verificar e insertar en una misma transacción** (D-13): `BEGIN IMMEDIATE`.
- **Reiniciar borra el archivo de la base** (D-16): los IDs vuelven a `R-0001`, sin `DELETE` ni `DROP` sobre `reservas`.
- **No cancelar reservas ya empezadas** (D-26), y validar antes de pedir confirmación (D-29).
- **Códigos de salida 0/1, también para errores de argumentos** (D-14, D-30); `disponibilidad` devuelve 0 cuando la consulta se completa (D-18).

### 4.2 Episodios de delegación

Hay cuatro episodios registrados.

El detalle de cada episodio (contexto, instrucción, acción del agente, motivo) está en [PROGRESO.md › Episodios de delegación](PROGRESO.md#episodios-de-delegación).

| Episodio | Objetivo | Decisión humana | Evidencia |
|---|---|---|---|
| [1 · Revisión de la especificación antes de programar](PROGRESO.md#episodio-1--revisión-de-la-especificación-antes-de-programar) | Confirmar que el agente interpretó la especificación antes de escribir código; el agente detectó 5 huecos | Aceptar el resumen y el plan, resolver los 5 huecos y rechazar la unión de las etapas 2 y 3 | Commit [`1191b03`](https://github.com/tbe02/reservas_laboratorio/commit/1191b03) |
| [2 · Import fuera de lugar y conexión sin cerrar](PROGRESO.md#episodio-2--import-fuera-de-lugar-y-conexión-sin-cerrar-en-persistenciapy) | Capa de persistencia de la etapa 1; el agente corrigió su propio import y una conexión sin cerrar | Revisar en la pantalla de aprobación las ediciones de corrección y aceptarlas | Commit [`1a43df8`](https://github.com/tbe02/reservas_laboratorio/commit/1a43df8); test `tests/test_persistencia.py::test_abrir_archivo_que_no_es_sqlite_se_trata_como_no_inicializada` |
| [3 · Pedido de registrar un rechazo humano que no ocurrió](PROGRESO.md#episodio-3--pedido-de-registrar-un-rechazo-humano-que-no-ocurrió) | Registro fiel de los episodios; el agente no escribió un rechazo que no había ocurrido | Aceptar la corrección del agente | Commit [`1a43df8`](https://github.com/tbe02/reservas_laboratorio/commit/1a43df8) (texto final del Episodio 2) |
| [4 · Fechas de 2030 en tests de punta a punta con hora real](PROGRESO.md#episodio-4--fechas-de-2030-en-tests-de-punta-a-punta-con-hora-real) | Tests de la CLI de punta a punta (etapa 5); el agente usó fechas de 2030 con hora real, que fallarían desde noviembre de 2030 | Corregir: pasar los tests a 2099 y cambiar la regla de fechas de `CLAUDE.md` | Commit [`fb8f240`](https://github.com/tbe02/reservas_laboratorio/commit/fb8f240); tests `test_punta_a_punta_*` en `tests/test_cli.py`; regla de fechas en `CLAUDE.md` |

Los incidentes del proceso (modo automático activo sin intención, pytest dentro de un pipe, huecos en las reglas de permisos) no son episodios de delegación. Están registrados en [PROGRESO.md › Entorno](PROGRESO.md#entorno-evidencia).
