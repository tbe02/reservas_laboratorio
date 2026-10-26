# Progreso

Archivo versionado de progreso, verificaciones y episodios de delegación. El agente lo lee al iniciar cada sesión y lo actualiza al terminar cada etapa (ver `CLAUDE.md`). El autor revisa y corrige cada actualización antes del commit.

---

## Entorno (evidencia)

Completar con la salida real copiada de la terminal, sin editarla.

```
$ claude --version
2.1.309 (Claude Code)
```

```
# Salida de /status dentro de Claude Code (pegar aquí; quitar datos de la cuenta si aparecen)
PENDIENTE
```

```
$ python --version
PENDIENTE
```

---

## Etapas

| # | Etapa | Estado | Commit |
|---|---|---|---|
| 0 | Especificación inicial y preparación del agente | Hecho (pendiente de commit) | |
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
