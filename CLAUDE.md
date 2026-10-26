# Instrucciones para el agente

## Proyecto

Sistema local de reservas de equipos de laboratorio. CLI en Python 3.14 con SQLite (módulo `sqlite3` de la biblioteca estándar) y pruebas con pytest.

La especificación completa está en `README.md`, sección 1. Es la fuente de verdad: no agregues funcionalidades, comandos ni parámetros que no estén ahí. Si algo no está especificado, preguntá antes de decidir.

## Al iniciar cada sesión

1. Leé `README.md` (sección 1), `PROGRESO.md` y `DECISIONES.md`.
2. Trabajá solo en la etapa que se te pida. No avances a la siguiente sin que te lo indiquen.

## Estilo

- Código, nombres, mensajes y comentarios en español (`crear_reserva`, `cancelar_reserva`, `ErrorValidacion`).
- Separar en capas: reglas de negocio, persistencia y CLI. La CLI no contiene reglas de negocio.
- CLI con `argparse` (biblioteca estándar). No agregar dependencias salvo pytest, con versión fija en `requirements.txt`.
- Mensajes de error claros para el usuario, sin trazas de Python.

## Regla de superposición y turnos consecutivos (crítica)

- Una reserva activa ocupa el intervalo semiabierto `[inicio, fin)`.
- Dos reservas activas de la misma unidad chocan si y solo si `inicio_A < fin_B and fin_A > inicio_B`. Usar comparaciones **estrictas** (`<`, `>`), nunca `<=` ni `>=`.
- 10:00–11:00 y 11:00–12:00 **no** chocan. Las reservas canceladas nunca bloquean.
- `reservar` y `disponibilidad` deben usar **la misma función** para detectar conflictos. No duplicar la lógica.
- Tests obligatorios: el ejemplo de la consigna (MIC-01 10–11 rechaza 10:30–11:30, permite 11–12; MIC-02 10–11 permitido con MIC-01 ocupado).

## Persistencia (crítica)

- Nunca usar `DELETE` sobre la tabla `reservas`. Cancelar = `UPDATE` del estado a `cancelada` y de `cancelada_en`.
- Verificar superposición e insertar dentro de la misma transacción (`BEGIN IMMEDIATE`).
- La ruta de la base se toma de la variable de entorno `RESERVAS_DB`; por defecto `datos/reservas.db`.
- Debe existir un test que cree una reserva activa y una cancelada, cierre la conexión, reabra la misma base y verifique ambas con su estado.

## El "ahora"

- Las funciones que dependen de la hora actual reciben `ahora=None` como parámetro opcional; si es `None`, usan la hora real de Buenos Aires.
- **Prohibido** leer el "ahora" de variables de entorno o de argumentos de la CLI: el usuario no debe poder saltear la regla de fechas pasadas.
- Los tests pasan siempre una fecha fija como `ahora` y usan fechas de 2030.
- Excepción: los tests que usan la hora real (camino `ahora=None` y tests de punta a punta de la CLI) y los ejemplos manuales del README usan fechas de 2099, para que sigan siendo futuras después de 2030.

## Pruebas

- Los tests usan siempre una base temporal (fixture con `tmp_path`); nunca `datos/reservas.db`.
- No ejecutes la aplicación contra `datos/reservas.db`. Para probarla a mano, usá `RESERVAS_DB=/tmp/<nombre>.db`.
- Antes de dar una etapa por terminada, ejecutá `.venv/bin/python -m pytest -v` y mostrá la salida real.
- Ejecutá pytest siempre con `.venv/bin/python -m pytest -v`: nunca dentro de un pipe ni con la salida filtrada (`| tail`, `| grep`, etc.), porque un pipe oculta el código de salida de pytest.
- Si pytest no corre o falla, no se commitea.
- La app y pytest se invocan siempre con el comando literal (`.venv/bin/python -m reservas …`, `.venv/bin/python -m pytest -v`), nunca mediante variables de shell (ej. `P=.venv/bin/python` y `$P -m reservas`) ni funciones de shell, para que se apliquen las reglas de permisos de `.claude/settings.json`.

## Honestidad en los resultados

- Nunca inventes salidas de comandos ni resultados de tests. Si algo no se ejecutó o falló, decilo.
- En la documentación, incluí solo salidas de comandos realmente ejecutados.

## Al terminar cada etapa

1. Actualizá la sección "Bitácora" de `PROGRESO.md`: qué se hizo, archivos tocados, resultado de pytest y pendientes.
2. Si tomaste una decisión técnica no prevista en la especificación, proponela para `DECISIONES.md` y esperá aprobación.
3. Proponé un mensaje de commit. No hagas `git push`.

## Datos

- Solo solicitantes ficticios. No uses datos reales de personas.
- No incluyas secretos, tokens ni credenciales en ningún archivo.
