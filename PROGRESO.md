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
- **Incidente de permisos:** el modo automático estuvo activo sin intención desde el inicio de la sesión (etapas 0 y 1). En ese período, las ediciones y el commit igual pidieron aprobación por las reglas ask de `.claude/settings.json` (para el commit, el mensaje fue: 'Ask rule Bash(git commit:*) overrides auto mode for this command'). Se volvió al modo manual antes de la etapa 2. Al reiniciar Claude Code antes del cierre de la etapa 3, el modo automático volvió a quedar activo; se volvió otra vez a modo manual. Para que Claude Code arranque en modo manual en este proyecto, se agregó `"defaultMode": "default"` a `.claude/settings.json` (README §3.4).
- **Incidente de verificación (pytest dentro de un pipe):** al cerrar la etapa 3, el agente corrió `python -m pytest -q 2>&1 | tail -1 && git add ... && git commit ...` en un solo comando. Después del reinicio el entorno virtual no estaba activado, así que `python` era `/usr/bin/python`, sin pytest: la salida fue `/usr/bin/python: No module named pytest`. Como el estado de salida del pipe es el de `tail`, el fallo no detuvo el `git add` ni el `git commit`, y el commit `4dc7f8d` se hizo sin la verificación. El agente lo informó en la misma respuesta y corrió `.venv/bin/python -m pytest -q` sobre lo commiteado: **90 passed in 0.28s**. Después de la última corrida del autor (90 passed) solo habían cambiado archivos de documentación. Para que no se repita, se agregó a `CLAUDE.md` (sección Pruebas): pytest se ejecuta siempre con `.venv/bin/python -m pytest -v`, nunca dentro de un pipe ni filtrado, y si pytest no corre o falla, no se commitea.
- **Hueco en reglas de instalación (detectado y cerrado):** la regla ask `Bash(pip install:*)` probablemente no cubría variantes como `python -m pip install`, el comando que usó el agente para instalar pytest en la etapa 1 con el modo automático activo. No se pudo confirmar si esa instalación pidió aprobación: el agente no ve la pantalla de aprobación y el autor no lo recuerda. Para cubrir las variantes se agregaron a la lista ask de `.claude/settings.json`: `Bash(python -m pip install:*)`, `Bash(python3 -m pip install:*)` y `Bash(pip3 install:*)`.
- **Hueco en la regla de ejecución de la app (detectado y cerrado):** en la prueba manual de la etapa 5, el agente ejecutó la app con `.venv/bin/python`. La regla ask `Bash(python -m reservas:*)` probablemente no cubría esa forma. Además, el comando no fue literal: definía `export RESERVAS_DB=/tmp/reservas_etapa5.db`, una variable `P=.venv/bin/python` y una función de shell que corría `$P -m reservas …`, una forma que probablemente tampoco coincide con reglas por prefijo. No se pudo confirmar si esa ejecución pidió aprobación: el agente no ve la pantalla de aprobación y el autor no lo puede confirmar. Se agregó a la lista ask de `.claude/settings.json` la regla `Bash(.venv/bin/python -m reservas:*)` (README §3.4). Las reglas por prefijo no cubren comandos armados con variables o funciones; la revisión humana del comando sigue siendo necesaria.
- **MCP:** 1 servidor conectado, `claude.ai Claude Docs` (8 herramientas), que proviene de la cuenta de claude.ai y no de la configuración del repositorio. No se usa en este proyecto: no se le pide al agente que lo utilice y todo el trabajo queda en archivos versionados del repositorio.
- **Entorno de Python:** entorno virtual `.venv` creado con `python3 -m venv .venv` y activado antes de abrir Claude Code. El agente usa `.venv/bin/python` explícitamente, aunque el entorno no esté activado en la sesión (ver incidente de verificación).
---

## Etapas

| # | Etapa | Estado | Commit |
|---|---|---|---|
| 0 | Especificación inicial y preparación del agente | Hecho | `6fd6135` |
| 1 | Estructura, base de datos e inventario | Hecho | `1a43df8` |
| 2 | Crear reserva y validaciones | Hecho | `51ef8a1` |
| 3 | Superposición y disponibilidad | Hecho | `4dc7f8d` |
| 4 | Cancelación | Hecho | `0665a5d` |
| 5 | CLI (comandos, confirmaciones, códigos de salida) | Hecho | `fb8f240` |
| 6 | Persistencia (test y procedimiento manual) | Pendiente | |
| 7 | Completar sección 2 del README | Pendiente | |

### Prompts de cada etapa (resumen)

| # | Instrucción dada al agente (extracto) |
|---|---|
| 0 | "Leé README.md, CLAUDE.md y PROGRESO.md. Resumime qué tenemos que construir y las reglas de superposición. Proponé un plan por etapas. No escribas código todavía." |
| 1 | "Etapa 1: creá la estructura del paquete `reservas/` y la capa de persistencia en SQLite según el esquema de la sección 1 del README. Incluí la carga del inventario de las 5 unidades y requirements.txt con pytest en versión fija. Escribí tests de que el inventario se carga correctamente." |
| 2 | "Etapa 2: implementá crear_reserva con todas las validaciones de la sección 1 (unidad existente, solicitante no vacío, fechas válidas, inicio < fin, no en el pasado). El "ahora" se recibe como parámetro opcional, como dice CLAUDE.md. Tests para cada caso inválido y para una creación válida." |
| 3 | "Etapa 3: implementá la detección de superposición y la consulta de disponibilidad usando UNA sola función compartida. Tests obligatorios: el ejemplo de la consigna (MIC-01 10-11 rechaza 10:30-11:30 y permite 11-12), MIC-02 10-11 permitido con MIC-01 ocupado, y que disponibilidad dé el mismo resultado que crear_reserva." |
| 4 | "Etapa 4: implementá cancelar_reserva. No borra el registro: cambia el estado y guarda cancelada_en. Error claro si no existe o ya está cancelada. Tests: el registro se conserva, el horario se libera (se puede volver a reservar) y la doble cancelación da error." |
| 5 | "Etapa 5: implementá la CLI con los comandos inicializar, unidades, disponibilidad, reservar, cancelar y listar, según la sección 1. inicializar y cancelar piden confirmación (s/n). Mensajes en español y código de salida 0 o 1. Agregá un par de tests de punta a punta de la CLI." |
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

### Etapa 4 · 2026-10-26
- **Hecho:** `reglas.cancelar_reserva(conexion, reserva_id_texto, ahora=None)`. Dentro de `BEGIN IMMEDIATE` busca la reserva, verifica que esté activa y la pasa a `cancelada` con `cancelada_en` (hora de Buenos Aires o el `ahora` recibido) mediante `persistencia.marcar_cancelada`, que hace un `UPDATE`; nunca `DELETE` (RN-11). Devuelve la reserva actualizada. Errores nuevos: `ErrorReservaNoEncontrada` (ID inexistente o mal escrito) y `ErrorReservaYaCancelada`; en ambos casos no se modifica nada (RN-12). El ID se acepta sin distinguir mayúsculas (`r-0001`, S-06) mediante `parsear_id_reserva`; `buscar_reserva` queda disponible para que la CLI muestre la reserva antes de confirmar (RF-04, etapa 5). El test de la etapa 3 `test_reserva_cancelada_no_bloquea` ahora usa la cancelación real en lugar del `UPDATE` simulado.
- **Archivos:** `reservas/reglas.py`, `reservas/persistencia.py`, `reservas/errores.py`, `tests/test_cancelar_reserva.py` (nuevo), `tests/test_superposicion.py`.
- **Pytest (informado por el agente):** `.venv/bin/python -m pytest -v` → 106 passed in 0.34s (16 de `test_cancelar_reserva.py`, 33 de `test_superposicion.py`, 48 de `test_crear_reserva.py` y 9 de `test_persistencia.py`).
- **Tests pedidos:** registro conservado (`test_cancelar_conserva_el_registro_y_sus_datos`), horario liberado y nuevo ID sin reutilizar el cancelado (`test_cancelar_libera_el_horario`, CA-07) y doble cancelación con error sin cambios (`test_doble_cancelacion_da_error_y_no_cambia_nada`, CA-08). Además: reserva inexistente, IDs mal escritos, que solo cambie la reserva indicada y, con `set_trace_callback`, que la cancelación ejecute `UPDATE` y ningún `DELETE` dentro de `BEGIN IMMEDIATE` … `COMMIT`.
- **Comprobación del agente:** `grep -rn --include='*.py' -i "delete" reservas/ tests/` → solo el docstring de `persistencia.py` ("Nunca se ejecuta DELETE…") y el test que lo verifica.
- **Pytest (ejecutado por el autor):** `.venv/bin/python -m pytest -v` → 106 passed in 0.32s (versión anterior a los cambios de D-25 y D-26).
- **Revisión humana:** se revisó el informe, el UPDATE de cancelación y el test de la secuencia; se verificó con grep que no hay DELETE; se aprobó D-25 y se decidió D-26.
- **Decisiones:** D-25 (formato de ID aceptado: `R-1` = `R-0001`), propuesta por el agente y aprobada por el autor. D-26 (no se cancelan reservas que ya empezaron), planteada por el agente como pregunta y decidida por el autor; reflejada en la especificación como S-19 y CA-18 (RF-04 remite a S-19). Ambas agregadas a `DECISIONES.md`.
- **Cambios tras la revisión:** `cancelar_reserva` rechaza con `ErrorValidacion` una reserva cuyo inicio es igual o anterior al "ahora" (D-26), sin modificar nada. Tests nuevos: `test_r_1_y_r_0001_son_la_misma_reserva` (D-25), `test_cancelar_una_reserva_que_ya_empezo_da_error_y_no_cambia_nada` (justo al inicio, en curso y terminada) y `test_cancelar_una_reserva_futura_se_permite`, todos con `ahora` fijo.
- **Pytest después de los cambios (agente):** `.venv/bin/python -m pytest -v` → 111 passed in 0.36s (21 de `test_cancelar_reserva.py`).
- **Pytest sobre la versión final (autor, previo al commit):** `.venv/bin/python -m pytest -v` → 111 passed in 0.33s.
- **Pendientes:** confirmación s/n y presentación en la CLI (etapa 5).

### Etapa 5 · 2026-10-26
- **Hecho:** CLI con `argparse` en `reservas/cli.py` y `reservas/__main__.py` (`python -m reservas <comando>`): `inicializar`, `unidades`, `disponibilidad`, `reservar`, `cancelar` y `listar`. La CLI solo interpreta argumentos, pide confirmaciones y muestra resultados; las reglas siguen en `reglas.py`. Códigos de salida 0/1 (S-10), también para errores de argumentos (argparse usa 2 por defecto; se cambió a 1). Errores en español por `stderr`, sin trazas; los mensajes de error más comunes de argparse se traducen. `inicializar` pide confirmación solo si hay reservas e informa cuántas (RF-06, S-14); `cancelar` muestra la reserva y pide confirmación (RF-04, S-08). `disponibilidad` aplica D-24 / S-18. Para no duplicar reglas en la CLI se agregaron `reglas.obtener_reserva_cancelable` (la usa también `cancelar_reserva`), `reglas.listar_reservas`, `persistencia.listar_reservas` y `persistencia.contar_reservas_en`.
- **Archivos:** `reservas/cli.py` (nuevo), `reservas/__main__.py` (nuevo), `reservas/reglas.py`, `reservas/persistencia.py`, `tests/test_cli.py` (nuevo).
- **Pytest (informado por el agente):** `.venv/bin/python -m pytest -v` → 164 passed in 1.91s (53 de `test_cli.py`).
- **Tests de la CLI:** 51 llaman a `main()` con `ahora` fijo y respuestas simuladas (CA-01, CA-11 a CA-18 por CLI, confirmaciones afirmativas y negativas, base no inicializada y sin tablas, errores sin traza, argumentos inválidos). 2 de punta a punta ejecutan `python -m reservas` en un proceso aparte con `RESERVAS_DB` temporal y la hora real (fechas de 2030 en la primera versión; pasadas a 2099 tras la revisión): reservar/choque/consecutiva/listar, y cancelar con `n` y `s` por la entrada estándar.
- **Prueba manual del agente:** con `export RESERVAS_DB=/tmp/reservas_etapa5.db` y una función de shell que ejecutaba `$P -m reservas …` con `P=.venv/bin/python`, no con el comando literal (ver "Hueco en la regla de ejecución de la app" en Entorno). Se probó: listar sin base, inicializar, unidades, reservas válidas, choque, consecutiva, otra unidad, disponibilidad ocupada/libre/pasada, fecha inexistente, cancelar con `n` y con `s`, doble cancelación, listar con filtros, inicializar con `n`, argumentos inválidos y `--help`. Todos los resultados y códigos de salida fueron los esperados. `datos/` siguió conteniendo solo `inventario.csv`.
- **Pytest (ejecutado por el autor):** `.venv/bin/python -m pytest -v` → 164 passed in 1.71s (versión anterior a pasar los tests de punta a punta a 2099 y a editar `CLAUDE.md`).
- **Prueba manual del autor:** con `RESERVAS_DB=/tmp/prueba_theo.db` y `.venv/bin/python`: `inicializar` creó la base; `unidades` listó las 5; se creó R-0001 (MIC-01 10–11); 10:30–11:30 dio error de choque con R-0001; se creó R-0002 (11–12); `disponibilidad` de 10 a 12 listó R-0001 y R-0002; `cancelar R-0001` mostró la reserva, se respondió `s` y la canceló; `listar` mostró R-0001 cancelada y R-0002 activa.
- **Revisión humana:** se revisó el informe y las decisiones; se detectó que los tests de punta a punta con hora real usaban fechas de 2030; se probó la app a mano.
- **Decisiones:** D-27 a D-30, propuestas por el agente y aprobadas por el autor; agregadas a `DECISIONES.md`.
- **Cambios tras la revisión:** los 2 tests de punta a punta pasaron de fechas de 2030 a 2099 (con hora real habrían empezado a fallar en noviembre de 2030), con un comentario que los marca como excepción a la regla de fecha fija de `CLAUDE.md`. Se agregó `Bash(.venv/bin/python -m reservas:*)` a la lista ask de `.claude/settings.json` y se actualizó README §3.4 (ver "Hueco en la regla de ejecución de la app" en Entorno).
- **Pytest después de los cambios (agente):** `.venv/bin/python -m pytest -v` → 164 passed in 1.84s.
- **Pytest sobre el commit `fb8f240` (autor):** `.venv/bin/python -m pytest -v` → 164 passed in 1.72s.
- **`CLAUDE.md` (antes del commit, a pedido del autor):** las fechas de 2030 quedan solo para tests con `ahora` fijo; los tests con hora real y los ejemplos manuales del README usan 2099. La app y pytest se invocan siempre con el comando literal (`.venv/bin/python -m …`), nunca mediante variables ni funciones de shell, para que se apliquen las reglas de permisos.
- **Pendientes:** etapa 6 (test de cierre y reapertura y procedimiento manual de persistencia). En el procedimiento manual del README (etapas 6 y 7), `RESERVAS_DB` se define con `export RESERVAS_DB=/tmp/...` en una línea aparte y después van los comandos literales (`.venv/bin/python -m reservas …`), como en la prueba manual del autor.

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
| 2026-10-26 | `.venv/bin/python -m pytest -v` | Etapa 4 (antes de D-25 y D-26) | 106 passed in 0.32s | Autor |
| 2026-10-26 | `grep -rn -i "delete" reservas/` | Etapa 4 | Solo el docstring de `reservas/persistencia.py:3` ("Nunca se ejecuta DELETE sobre `reservas`") y el `.pyc` compilado. No hay `DELETE` en el código. | Autor |
| 2026-10-26 | `.venv/bin/python -m pytest -v` | Etapa 4, versión final (previa al commit) | 111 passed in 0.33s | Autor |
| 2026-10-26 | `.venv/bin/python -m pytest -v` | Etapa 5 (antes de pasar los tests de punta a punta a 2099 y de editar `CLAUDE.md`) | 164 passed in 1.71s | Autor |
| 2026-10-26 | `.venv/bin/python -m pytest -v` | `fb8f240` (etapa 5) | 164 passed in 1.72s | Autor |
| 2026-10-26 | Prueba manual de la CLI con `RESERVAS_DB=/tmp/prueba_theo.db` y `.venv/bin/python -m reservas`: `inicializar`, `unidades`, `reservar` (R-0001 MIC-01 10–11), `reservar` 10:30–11:30, `reservar` (R-0002 11–12), `disponibilidad` 10–12, `cancelar R-0001` con `s`, `listar` | Etapa 5 | Base creada; 5 unidades; R-0001 creada; choque con R-0001; R-0002 creada; disponibilidad listó R-0001 y R-0002; cancelar mostró la reserva y la canceló; `listar`: R-0001 cancelada y R-0002 activa | Autor |

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
