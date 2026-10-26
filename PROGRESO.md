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
| 1 | |
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

---

## Verificaciones ejecutadas

Solo comprobaciones realmente ejecutadas por el autor. Si algo falló o no se ejecutó, se registra igual.

| Fecha | Comando / procedimiento | Versión (commit) | Resultado observado | Ejecutado por |
|---|---|---|---|---|
| | | | | |

---

## Episodios de delegación

Registrar solo episodios reales, en el momento en que ocurren. No inventar fallas ni pegar transcripciones completas.

### Episodio 1 · Título

- **Objetivo y requisito:** (ej. RN-08 turnos consecutivos, CA-04)
- **Contexto suministrado:** (archivos que leyó el agente)
- **Extracto de la instrucción:** "…"
- **Acción o resultado del agente:**
- **Decisión humana:** aceptar / corregir / rechazar
- **Motivo:**
- **Evidencia:** commit `abc1234`, test `tests/...::test_...`, salida de pytest

### Episodio 2 · Título

- **Objetivo y requisito:**
- **Contexto suministrado:**
- **Extracto de la instrucción:**
- **Acción o resultado del agente:**
- **Decisión humana:**
- **Motivo:**
- **Evidencia:**

### Episodio 3 · Título

- **Objetivo y requisito:**
- **Contexto suministrado:**
- **Extracto de la instrucción:**
- **Acción o resultado del agente:**
- **Decisión humana:**
- **Motivo:**
- **Evidencia:**
