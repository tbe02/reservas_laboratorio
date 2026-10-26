# Progreso

Archivo versionado de progreso, verificaciones y episodios de delegación. El agente lo lee al iniciar cada sesión y lo actualiza al terminar cada etapa (ver `CLAUDE.md`). El autor revisa y corrige cada actualización antes del commit.

---

## Entorno (evidencia)

```
# Salida de /status dentro de Claude Code (2026-10-26).
# Se quitaron: Session ID, Peer address, Organization y Email.
Version:           2.1.309
Session kind:      interactive
cwd:               /home/theo/Documents/reservas_laboratorio
Login method:      Claude Pro account
Model:             opus (claude-opus-5-5)
MCP servers:       1 connected
Setting sources:   User settings, Shared project settings
Auto mode server:  Enabled
```

```
$ python --version
Python 3.14.8
```

- **Modelo:** Claude Opus 5.5 (`claude-opus-5-5`). Esfuerzo alto: no aparece en `/status`, pero la interfaz de Claude Code muestra el indicador `high · /effort`.
- **Configuración del proyecto:** "Shared project settings" confirma que se aplica `.claude/settings.json` del repositorio.
- **Modo de permisos:** se trabaja en modo manual. Las reglas ask de `.claude/settings.json` obligan a pedir aprobación para editar, ejecutar la app y commitear, sea cual sea el modo activo (ver incidente).
- **Incidente de permisos:** el modo automático estuvo activo sin intención desde el inicio de la sesión (etapas 0 y 1). En ese período, las ediciones y el commit igual pidieron aprobación por las reglas ask de `.claude/settings.json` (para el commit, el mensaje fue: 'Ask rule Bash(git commit:*) overrides auto mode for this command'). Se volvió al modo manual antes de la etapa 2.
- **Hueco en reglas de instalación (detectado y cerrado):** la regla ask `Bash(pip install:*)` probablemente no cubría variantes como `python -m pip install`, el comando que usó el agente para instalar pytest en la etapa 1 con el modo automático activo. No se pudo confirmar si esa instalación pidió aprobación: el agente no ve la pantalla de aprobación y el autor no lo recuerda. Para cubrir las variantes se agregaron a la lista ask de `.claude/settings.json`: `Bash(python -m pip install:*)`, `Bash(python3 -m pip install:*)` y `Bash(pip3 install:*)`.
- **MCP:** 1 servidor conectado, `claude.ai Claude Docs` (8 herramientas), que proviene de la cuenta de claude.ai y no de la configuración del repositorio. No se usa en este proyecto: no se le pide al agente que lo utilice y todo el trabajo queda en archivos versionados del repositorio.
- **Entorno de Python:** entorno virtual `.venv` creado con `python3 -m venv .venv` y activado antes de abrir Claude Code.
---

## Etapas

| # | Etapa | Estado | Commit |
|---|---|---|---|
| 0 | Especificación inicial y preparación del agente | Hecho | `6fd6135` |
| 1 | Estructura, base de datos e inventario | Hecho | `1a43df8` |
| 2 | Crear reserva y validaciones | Hecho | `51ef8a1` |
| 3 | Superposición y disponibilidad | Pendiente | |
| 4 | Cancelación | Pendiente | |
| 5 | CLI (comandos, confirmaciones, códigos de salida) | Pendiente | |
| 6 | Persistencia (test y procedimiento manual) | Pendiente | |
| 7 | Completar sección 2 del README | Pendiente | |

### Prompts de cada etapa (resumen)

| # | Instrucción dada al agente (extracto) |
|---|---|
| 0 | "Leé README.md, CLAUDE.md y PROGRESO.md. Resumime qué tenemos que construir y las reglas de superposición. Proponé un plan por etapas. No escribas código todavía." |
| 1 | "Etapa 1: creá la estructura del paquete `reservas/` y la capa de persistencia en SQLite según el esquema de la sección 1 del README. Incluí la carga del inventario de las 5 unidades y requirements.txt con pytest en versión fija. Escribí tests de que el inventario se carga correctamente." |
| 2 | "Etapa 2: implementá crear_reserva con todas las validaciones de la sección 1 (unidad existente, solicitante no vacío, fechas válidas, inicio < fin, no en el pasado). El "ahora" se recibe como parámetro opcional, como dice CLAUDE.md. Tests para cada caso inválido y para una creación válida." |
| 3 | "Etapa 3: implementá la detección de superposición y la consulta de disponibilidad usando UNA sola función compartida. Tests obligatorios: el ejemplo de la consigna (MIC-01 10-11 rechaza 10:30-11:30 y permite 11-12), MIC-02 10-11 permitido con MIC-01 ocupado, y que disponibilidad dé el mismo resultado que crear_reserva." |
| 4 | |
| 5 | |
| 6 | |
| 7 | |

---

## Bitácora

<!-- Una entrada por etapa. Formato:

### Etapa N · AAAA-MM-DD
- **Hecho:**
- **Archivos:**
- **Pytest (informado por el agente):**
- **Pytest (ejecutado por el autor):** comando + resultado
- **Revisión humana:** qué se revisó, qué se aceptó o corrigió
- **Pendientes:**
-->

### Etapa 1 · 2026-10-26
- **Hecho:** paquete `reservas/` con la capa de persistencia: esquema de §1.8, ruta de la base según `RESERVAS_DB` (por defecto `datos/reservas.db`), carga del inventario desde `datos/inventario.csv`, recreación de la base borrando el archivo (S-13) y error de base no inicializada si el archivo no existe, no tiene las tablas o no es SQLite (S-09, S-17). Se instaló `pytest==9.1.1` en `.venv`.
- **Archivos:** `requirements.txt`, `reservas/__init__.py`, `reservas/errores.py`, `reservas/persistencia.py`, `tests/conftest.py`, `tests/test_persistencia.py`.
- **Pytest (informado por el agente):** `python -m pytest -v` → 9 passed in 0.05s (Python 3.14.8, pytest 9.1.1).
- **Pytest (ejecutado por el autor):** `python -m pytest -v` → 9 passed in 0.04s (Python 3.14.8, pytest 9.1.1). `datos/` contiene solo `inventario.csv` después de correr los tests.
- **Revisión humana:** algunas ediciones se aprobaron sin revisarlas en el momento; se revisaron completas con `git diff` antes del commit. Se aprobó D-21.
- **Decisiones:** D-21 (rutas por defecto desde la raíz del proyecto), propuesta por el agente y aprobada por el autor; agregada a `DECISIONES.md`.
- **Pendientes:** confirmación de `inicializar` y mensajes (etapa 5); `__main__.py` y CLI (etapa 5).

### Etapa 2 · 2026-10-26
- **Hecho:** `crear_reserva(conexion, unidad, solicitante, inicio, fin, ahora=None)` en la nueva capa de reglas, con las validaciones RN-01 a RN-05: unidad existente (sin distinguir mayúsculas), solicitante no vacío y recortado (S-06), formato `AAAA-MM-DD HH:MM` estricto y fecha existente, inicio anterior al fin, inicio posterior al "ahora". Si `ahora` es `None` se usa la hora real de Buenos Aires. Los errores se lanzan como `ErrorValidacion` con mensajes en español. `formatear_id_reserva` muestra los IDs como `R-0001`. En persistencia se agregaron `existe_unidad`, `insertar_reserva` y `obtener_reserva`.
- **Archivos:** `reservas/reglas.py` (nuevo), `reservas/errores.py`, `reservas/persistencia.py`, `tests/test_crear_reserva.py` (nuevo).
- **Pytest (informado por el agente):** `python -m pytest -v` → 57 passed in 0.17s (48 de `test_crear_reserva.py` y 9 de `test_persistencia.py`).
- **Pytest (ejecutado por el autor):** `python -m pytest -v` → 57 passed in 0.17s (Python 3.14.8, pytest 9.1.1).
- **Revisión humana:** se revisó el informe de la etapa (validaciones, orden, manejo del ahora y tests); se aprobó D-22; se decidió mantener que las fechas no se recorten (D-23); se pidió agregar tests del camino `ahora=None` con años 2099 y 2000; se verificó con `grep` que el ahora no se lee de variables de entorno.
- **Decisiones:** D-22 (interpretación del parámetro `ahora`), propuesta por el agente y aprobada por el autor. D-23 (las fechas no se recortan), señalada por el agente y decidida por el autor. Ambas agregadas a `DECISIONES.md`.
- **Tests del camino `ahora=None`:** a pedido del autor se agregaron dos tests que usan la hora real (reserva en 2099 aceptada, en 2000 rechazada). Son una excepción aprobada a la regla de fecha fija de `CLAUDE.md` y lo aclara un comentario en el test.
- **Pendientes:** `crear_reserva` todavía **no** detecta superposiciones ni usa `BEGIN IMMEDIATE` (etapa 3).

### Etapa 3 · 2026-10-26
- **Hecho:** detección de superposición con una única consulta, `persistencia.buscar_conflictos` (la de §1.8, con `<` y `>` estrictos y filtro `estado = 'activa'`). `reglas.consultar_disponibilidad` es la función compartida (RN-10): valida RN-01, RN-03 y RN-04, busca conflictos y devuelve un resultado con `libre`, `en_pasado`, `reservable` y la lista de reservas que bloquean. `crear_reserva` llama a `consultar_disponibilidad` dentro de `persistencia.transaccion_inmediata` (`BEGIN IMMEDIATE`; `ROLLBACK` si hay error, D-13) y lanza `ErrorSuperposicion` (nuevo), con un mensaje que indica las reservas que bloquean.
- **Archivos:** `reservas/persistencia.py`, `reservas/reglas.py`, `reservas/errores.py`, `tests/test_superposicion.py` (nuevo).
- **Pytest (informado por el agente):** `python -m pytest -v` → 90 passed in 0.35s (33 de `test_superposicion.py`, 48 de `test_crear_reserva.py` y 9 de `test_persistencia.py`).
- **Tests obligatorios:** `test_consigna_rechaza_mic01_de_10_30_a_11_30` (CA-03), `test_consigna_permite_mic01_de_11_a_12` (CA-04), `test_consigna_permite_mic02_de_10_a_11_con_mic01_ocupado` (CA-05) y `test_disponibilidad_coincide_con_crear_reserva` con 8 casos (CA-09).
- **Prueba de mutación (agente, sobre una copia en el scratchpad; el repositorio no se modificó):** con `<=`/`>=` en la consulta fallan 6 tests (los de turnos consecutivos); sin el filtro `estado = 'activa'` falla `test_reserva_cancelada_no_bloquea`. Detalle, comandos y bloqueo de la regla deny en [Prueba de mutación: turnos consecutivos](#prueba-de-mutación-turnos-consecutivos).
- **Pytest (ejecutado por el autor):** `python -m pytest -v` → 90 passed in 0.27s (Python 3.14.8, pytest 9.1.1).
- **Revisión humana:** se revisó el informe, la consulta de superposición y la prueba de mutación; se verificó con `grep` que la consulta usa comparaciones estrictas y con `git status` que no quedaron restos de la mutación.
- **Decisiones:** D-24 (un intervalo en el pasado y ocupado muestra ambas cosas en `disponibilidad`), planteada por el agente como pregunta y decidida por el autor; se aplica en la etapa 5.
- **Pendientes:** el test de que una reserva cancelada no bloquea simula la cancelación con un `UPDATE` directo; la cancelación real llega en la etapa 4 (CA-07). Aplicar D-24 en la CLI (etapa 5).

---

## Verificaciones ejecutadas

Solo comprobaciones realmente ejecutadas por el autor. Si algo falló o no se ejecutó, se registra igual.

| Fecha | Comando / procedimiento | Versión (commit) | Resultado observado | Ejecutado por |
|---|---|---|---|---|
| 2026-10-26 | `python -m pytest -v` | Etapa 1 | 9 passed in 0.04s | Autor |
| 2026-10-26 | `ls datos/` después de los tests | Etapa 1 | Solo `inventario.csv` | Autor |
| 2026-10-26 | `python -m pytest -v` | Etapa 2 | 57 passed in 0.17s | Autor |
| 2026-10-26 | `grep -rn "environ" reservas/` | Etapa 2 | Única coincidencia en código fuente: `reservas/persistencia.py:45` (`os.environ.get("RESERVAS_DB")`). También coincidió el binario `reservas/__pycache__/persistencia.cpython-314.pyc`. El "ahora" no se lee de variables de entorno. | Autor |
| 2026-10-26 | `python -m pytest -v` | Etapa 3 | 90 passed in 0.27s (Python 3.14.8, pytest 9.1.1) | Autor |
| 2026-10-26 | `git status` después de la prueba de mutación | Etapa 3 | Solo cambios de la etapa 3 (`PROGRESO.md`, `errores.py`, `persistencia.py`, `reglas.py` y `tests/test_superposicion.py` nuevo); no quedaron restos de la mutación | Autor |
| 2026-10-26 | `grep -n "inicio <\|fin >" reservas/persistencia.py` | Etapa 3 | Líneas 170-171: `AND inicio < :fin_nuevo` y `AND fin > :inicio_nuevo` (estrictas); línea 35: `CHECK (inicio < fin)` | Autor |

---

## Prueba de mutación: turnos consecutivos

Evidencia de la adaptación específica 1 del README (§3.5). La ejecutó el agente en la etapa 3 sobre copias de `reservas/`, `tests/` y `datos/inventario.csv` en su carpeta temporal de sesión (scratchpad), fuera del repositorio. El autor verificó después con `git status` que el repositorio no quedó modificado.

**Objetivo:** comprobar que los tests detectan si la consulta de superposición deja de usar comparaciones estrictas o deja de ignorar las reservas canceladas.

| Mutación | Qué se cambió en `buscar_conflictos` | Resultado |
|---|---|---|
| Comparaciones no estrictas | `inicio < :fin_nuevo` → `inicio <= :fin_nuevo` y `fin > :inicio_nuevo` → `fin >= :inicio_nuevo` | 6 failed, 84 passed |
| Sin filtro de estado | se quitó la línea `AND estado = 'activa'` | 1 failed, 89 passed |

Tests que fallaron con comparaciones no estrictas:

```
FAILED tests/test_superposicion.py::test_consigna_permite_mic01_de_11_a_12 - ...
FAILED tests/test_superposicion.py::test_turno_consecutivo_anterior_se_permite
FAILED tests/test_superposicion.py::test_disponibilidad_libre - AssertionErro...
FAILED tests/test_superposicion.py::test_disponibilidad_lista_todas_las_reservas_que_bloquean
FAILED tests/test_superposicion.py::test_disponibilidad_coincide_con_crear_reserva[MIC-01-2030-11-03 11:00-2030-11-03 12:00-True]
FAILED tests/test_superposicion.py::test_disponibilidad_coincide_con_crear_reserva[MIC-01-2030-11-03 09:00-2030-11-03 10:00-True]
6 failed, 84 passed in 0.34s
```

Test que falló sin el filtro de estado:

```
FAILED tests/test_superposicion.py::test_reserva_cancelada_no_bloquea - Asser...
1 failed, 89 passed in 0.29s
```

Comandos usados (`SCRATCHPAD` = `/tmp/claude-1000/-home-theo-Documents-reservas-laboratorio/fa0163b8-a12f-474a-9022-7c77024ce616/scratchpad`):

```bash
# Mutación 1: comparaciones no estrictas
S=$SCRATCHPAD/mutacion-estricta && mkdir -p "$S/datos" && cd /home/theo/Documents/reservas_laboratorio && cp -r reservas tests "$S/" && cp datos/inventario.csv "$S/datos/" && cd "$S" && sed -i 's/"AND inicio < :fin_nuevo "/"AND inicio <= :fin_nuevo "/; s/"AND fin > :inicio_nuevo "/"AND fin >= :inicio_nuevo "/' reservas/persistencia.py && grep -n "inicio <=\|fin >=" reservas/persistencia.py && python -m pytest -q -p no:cacheprovider 2>&1 | grep -E "FAILED|passed|failed"

# Mutación 2: sin filtro de estado
S=$SCRATCHPAD/mutacion-estado && mkdir -p "$S/datos" && cd /home/theo/Documents/reservas_laboratorio && cp -r reservas tests "$S/" && cp datos/inventario.csv "$S/datos/" && cd "$S" && sed -i "/\"AND estado = 'activa' \"/d" reservas/persistencia.py && sed -n '165,172p' reservas/persistencia.py && python -m pytest -q -p no:cacheprovider 2>&1 | grep -E "FAILED|passed|failed"
```

(En los comandos ejecutados, `$SCRATCHPAD` estaba escrito como la ruta completa.)

**Bloqueo de la regla deny.** El primer intento de la mutación 1 fue rechazado por la regla `Bash(rm -rf:*)` de `.claude/settings.json`, porque incluía dos `rm -rf` (para limpiar la carpeta temporal y los `__pycache__` copiados). Los dos apuntaban a la carpeta temporal, no al repositorio. El agente no insistió con el mismo comando: lo reescribió sin `rm -rf` usando carpetas nuevas. Comando bloqueado, exacto:

```bash
S=/tmp/claude-1000/-home-theo-Documents-reservas-laboratorio/fa0163b8-a12f-474a-9022-7c77024ce616/scratchpad/mutacion && rm -rf "$S" && mkdir -p "$S/datos" && cd /home/theo/Documents/reservas_laboratorio && cp -r reservas tests "$S/" && cp datos/inventario.csv "$S/datos/" && rm -rf "$S"/reservas/__pycache__ "$S"/tests/__pycache__ && cd "$S" && sed -i 's/"AND inicio < :fin_nuevo "/"AND inicio <= :fin_nuevo "/; s/"AND fin > :inicio_nuevo "/"AND fin >= :inicio_nuevo "/' reservas/persistencia.py && grep -n "inicio <=\|fin >=" reservas/persistencia.py && python -m pytest -q -p no:cacheprovider 2>&1 | grep -E "FAILED|passed|failed"
```

---

## Episodios de delegación

Registrar solo episodios reales, en el momento en que ocurren. No inventar fallas ni pegar transcripciones completas.

### Episodio 1 · Revisión de la especificación antes de programar

- **Objetivo y requisito:** confirmar que el agente interpretó la especificación (README §1) antes de escribir código.
- **Contexto suministrado:** README.md, CLAUDE.md, PROGRESO.md y DECISIONES.md.
- **Extracto de la instrucción:** "Resumime en pocas líneas qué tenemos que construir y las reglas de superposición. Después proponé un plan por etapas. No escribas código todavía."
- **Acción o resultado del agente:** resumió correctamente los 6 comandos, la regla `inicio_A < fin_B and fin_A > inicio_B` con comparación estricta, que cancelar no borra y el "ahora" como parámetro. Propuso un plan de 7 etapas y detectó 5 huecos: reinicio vs. IDs no reutilizables y prohibición de DELETE, `inicializar` sin reservas, código de salida de `disponibilidad` cuando está ocupada, orden y columnas de `listar`, y archivo de base sin tablas. Ofreció unir las etapas 2 y 3.
- **Decisión humana:** aceptar el resumen y el plan; resolver los 5 huecos; rechazar la unión de etapas 2 y 3.
- **Motivo:** los huecos eran ambigüedades reales que habrían obligado al agente a suponer. Se mantuvieron las etapas separadas para revisar las validaciones y la regla de superposición por separado.
- **Evidencia:** commit `1191b03` (README §1 y DECISIONES.md D-16 en adelante).

### Episodio 2 · Import fuera de lugar y conexión sin cerrar en `persistencia.py`

- **Objetivo y requisito:** capa de persistencia de la etapa 1 (S-09, S-17).
- **Contexto suministrado:** README §1, CLAUDE.md, PROGRESO.md, DECISIONES.md.
- **Extracto de la instrucción:** "Etapa 1: creá la estructura del paquete `reservas/` y la capa de persistencia en SQLite…"
- **Acción o resultado del agente:** escribió el import de `ErrorBaseNoInicializada` al final de `persistencia.py` con `# noqa: E402`, sin que hubiera importación circular. En el mismo turno, antes de cualquier revisión humana, se corrigió solo y movió el import arriba. Al corregirlo detectó y arregló además que `abrir_base` no cerraba la conexión ante un archivo que no es SQLite.
- **Decisión humana:** revisar en la pantalla de aprobación las ediciones de corrección (import movido arriba sin noqa y `conexion.close()` en `abrir_base`) y aceptarlas.
- **Motivo:** el resultado final es correcto. El error de origen muestra que hace falta revisar el código del agente aunque los tests pasen: la primera versión también los habría pasado.
- **Evidencia:** commit `1a43df8`; test `tests/test_persistencia.py::test_abrir_archivo_que_no_es_sqlite_se_trata_como_no_inicializada`.

### Episodio 3 · Pedido de registrar un rechazo humano que no ocurrió

- **Objetivo y requisito:** registro fiel de episodios en PROGRESO.md (regla de honestidad de CLAUDE.md; "registrar solo episodios reales" de PROGRESO.md).
- **Contexto suministrado:** CLAUDE.md, PROGRESO.md y la conversación de la etapa 1.
- **Extracto de la instrucción:** "Completá el Episodio 2: proponías el import al final con "# noqa: E402", yo lo rechacé y pedí moverlo arriba y explicar si había importación circular…"
- **Acción o resultado del agente:** no escribió esa versión. Señaló que el rechazo y el pedido de explicación no habían ocurrido (la corrección fue del propio agente, en el mismo turno), citó la regla de honestidad de CLAUDE.md y la de PROGRESO.md de registrar solo episodios reales, y propuso una versión fiel. No hizo el commit hasta tener confirmación.
- **Decisión humana:** aceptar la corrección del agente.
- **Motivo:** la versión pedida era incorrecta: el autor no había rechazado el cambio.
- **Evidencia:** el texto final del Episodio 2 en PROGRESO.md.
