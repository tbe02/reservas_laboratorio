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
- **Modo de permisos:** se trabaja en el modo normal (pide aprobación antes de editar). El modo automático está disponible pero **no se usa**.
- **MCP:** 1 servidor conectado, `claude.ai Claude Docs` (8 herramientas), que proviene de la cuenta de claude.ai y no de la configuración del repositorio. No se usa en este proyecto: no se le pide al agente que lo utilice y todo el trabajo queda en archivos versionados del repositorio.
- **Entorno de Python:** entorno virtual `.venv` creado con `python3 -m venv .venv` y activado antes de abrir Claude Code.
---

## Etapas

| # | Etapa | Estado | Commit |
|---|---|---|---|
| 0 | Especificación inicial y preparación del agente | Hecho | `6fd6135` |
| 1 | Estructura, base de datos e inventario | Pendiente | |
| 2 | Crear reserva y validaciones | Pendiente | |
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
| 2 | |
| 3 | |
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

---

## Verificaciones ejecutadas

Solo comprobaciones realmente ejecutadas por el autor. Si algo falló o no se ejecutó, se registra igual.

| Fecha | Comando / procedimiento | Versión (commit) | Resultado observado | Ejecutado por |
|---|---|---|---|---|
| 2026-10-26 | `python -m pytest -v` | Etapa 1 | 9 passed in 0.04s | Autor |
| 2026-10-26 | `ls datos/` después de los tests | Etapa 1 | Solo `inventario.csv` | Autor |

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
- **Evidencia:** commit `COMPLETAR` (README §1 y DECISIONES.md D-16 en adelante).

### Episodio 2 · Import fuera de lugar y conexión sin cerrar en `persistencia.py`

- **Objetivo y requisito:** capa de persistencia de la etapa 1 (S-09, S-17).
- **Contexto suministrado:** README §1, CLAUDE.md, PROGRESO.md, DECISIONES.md.
- **Extracto de la instrucción:** "Etapa 1: creá la estructura del paquete `reservas/` y la capa de persistencia en SQLite…"
- **Acción o resultado del agente:** escribió el import de `ErrorBaseNoInicializada` al final de `persistencia.py` con `# noqa: E402`, sin que hubiera importación circular. En el mismo turno, antes de cualquier revisión humana, se corrigió solo y movió el import arriba. Al corregirlo detectó y arregló además que `abrir_base` no cerraba la conexión ante un archivo que no es SQLite.
- **Decisión humana:** revisar en la pantalla de aprobación las ediciones de corrección (import movido arriba sin noqa y `conexion.close()` en `abrir_base`) y aceptarlas.
- **Motivo:** el resultado final es correcto. El error de origen muestra que hace falta revisar el código del agente aunque los tests pasen: la primera versión también los habría pasado.
- **Evidencia:** commit `COMPLETAR`; test `tests/test_persistencia.py::test_abrir_archivo_que_no_es_sqlite_se_trata_como_no_inicializada`.

### Episodio 3 · Pedido de registrar un rechazo humano que no ocurrió

- **Objetivo y requisito:** registro fiel de episodios en PROGRESO.md (regla de honestidad de CLAUDE.md; "registrar solo episodios reales" de PROGRESO.md).
- **Contexto suministrado:** CLAUDE.md, PROGRESO.md y la conversación de la etapa 1.
- **Extracto de la instrucción:** "Completá el Episodio 2: proponías el import al final con "# noqa: E402", yo lo rechacé y pedí moverlo arriba y explicar si había importación circular…"
- **Acción o resultado del agente:** no escribió esa versión. Señaló que el rechazo y el pedido de explicación no habían ocurrido (la corrección fue del propio agente, en el mismo turno), citó la regla de honestidad de CLAUDE.md y la de PROGRESO.md de registrar solo episodios reales, y propuso una versión fiel. No hizo el commit hasta tener confirmación.
- **Decisión humana:** aceptar la corrección del agente.
- **Motivo:** la versión pedida era incorrecta: el autor no había rechazado el cambio.
- **Evidencia:** el texto final del Episodio 2 en PROGRESO.md.
