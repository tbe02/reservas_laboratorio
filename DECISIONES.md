# Registro de decisiones

Cada decisión indica contexto, decisión, alternativas consideradas y consecuencias.

Las decisiones D-01 a D-15 se tomaron en la **fase de planificación**, antes de que el agente de programación escribiera código. Esa planificación se hizo en una conversación de chat aparte (no incluida en el repositorio); estas decisiones **no** son episodios de delegación. Los episodios se registran en [PROGRESO.md](PROGRESO.md#episodios-de-delegación).

Las decisiones nuevas que surjan durante la construcción se agregan al final con el commit correspondiente.

---

## D-01 · Lenguaje: Python 3.14 con pytest

- **Contexto:** la consigna deja libre el lenguaje y exige pruebas automáticas reproducibles sin la cuenta del autor.
- **Decisión:** Python 3.14 (versión instalada: 3.14.8) y pytest como única dependencia externa.
- **Alternativas:** JavaScript/Node con Jest; Java con JUnit; C# con xUnit.
- **Consecuencias:** pocas dependencias y `sqlite3` incluido en la biblioteca estándar. Se requiere Python 3.14 o compatible para reproducir.

## D-02 · Interfaz: CLI

- **Contexto:** la consigna acepta consola o API local; la interfaz gráfica no es obligatoria y un frente complejo queda fuera de alcance.
- **Decisión:** CLI con `argparse`, ejecutada como `python -m reservas <comando>`.
- **Alternativas:** API REST local con FastAPI; ambas sobre un núcleo común; interfaz gráfica.
- **Consecuencias:** sin servidor ni dependencias extra; el corrector reproduce todo copiando comandos. Menos "realista" que una API, pero suficiente para el alcance.

## D-03 · Persistencia: SQLite

- **Contexto:** hay que conservar reservas y estados entre ejecuciones.
- **Decisión:** un archivo SQLite (`datos/reservas.db`, excluido de Git), configurable con la variable de entorno `RESERVAS_DB`.
- **Alternativas:** archivo JSON; CSV.
- **Consecuencias:** transacciones y restricciones (`CHECK`) nativas, sin servidor. El archivo no es legible a simple vista como un JSON.

## D-04 · Intervalos semiabiertos `[inicio, fin)` con comparación estricta

- **Contexto:** la consigna exige rechazar superposiciones y permitir límites consecutivos (10–11 y 11–12).
- **Decisión:** dos reservas activas de la misma unidad chocan si y solo si `inicio_A < fin_B` y `fin_A > inicio_B`.
- **Alternativas:** intervalos cerrados `[inicio, fin]` con `<=`, que harían chocar los turnos consecutivos.
- **Consecuencias:** los turnos consecutivos se permiten sin casos especiales. Es la adaptación específica principal en `CLAUDE.md`.

## D-05 · Una sola función de conflictos para reservar y consultar

- **Contexto:** la consigna pide que la disponibilidad use las mismas reglas que la creación.
- **Decisión:** `reservar` y `disponibilidad` usan la misma función para detectar conflictos.
- **Alternativas:** implementar la consulta por separado.
- **Consecuencias:** es imposible que una diga "libre" y la otra rechace. Se verifica con CA-09.

## D-06 · Fechas en hora de Buenos Aires, formato `AAAA-MM-DD HH:MM`, guardadas como texto

- **Contexto:** la consigna pide documentar zona horaria y formato.
- **Decisión:** todas las fechas se interpretan en `America/Argentina/Buenos_Aires` y se guardan como texto con formato fijo.
- **Alternativas:** UTC con ISO 8601; formato `DD/MM/AAAA`.
- **Consecuencias:** con formato y zona únicos, el texto se ordena y compara correctamente en SQL y es legible. No se soportan otras zonas horarias.

## D-07 · Rechazar reservas en el pasado

- **Contexto:** la consigna pide documentar el tratamiento de fechas pasadas.
- **Decisión:** el inicio de una reserva nueva debe ser posterior al momento actual.
- **Alternativas:** permitir reservas pasadas (registro retroactivo).
- **Consecuencias:** el historial no se llena de reservas imposibles. Obliga a controlar el "ahora" en las pruebas (ver D-08).

## D-08 · El "ahora" como parámetro, no como variable de entorno

- **Contexto:** con D-07, las pruebas dependerían de la fecha en que se ejecutan. Se propuso inicialmente una variable de entorno `RESERVAS_AHORA` para fijar la hora.
- **Decisión:** descartar `RESERVAS_AHORA`. Las funciones reciben `ahora=None` como parámetro opcional; la CLI siempre usa la hora real y los tests pasan una fecha fija.
- **Alternativas:** variable de entorno `RESERVAS_AHORA`; reemplazar la función de hora en los tests (monkeypatch).
- **Motivo del cambio:** la variable de entorno permitía que cualquier usuario salteara la regla de fechas pasadas escribiendo una fecha falsa delante del comando.
- **Consecuencias:** la regla no se puede saltear desde la CLI y las pruebas son reproducibles. Los ejemplos manuales usan fechas de 2030. Si el reloj del sistema está mal, el sistema usa esa hora (limitación declarada).

## D-09 · Sin límites de duración ni anticipación

- **Contexto:** la consigna pide documentar estos límites "si se aplican".
- **Decisión:** no se aplican; una reserva puede cruzar la medianoche.
- **Alternativas:** duración máxima (ej. 8 h); anticipación máxima (ej. 90 días); bloques de 15/30 min.
- **Consecuencias:** menos reglas y supuestos que justificar. Una reserva podría bloquear una unidad por un período muy largo.

## D-10 · Cancelar cambia el estado; nunca se borra

- **Contexto:** la consigna pide cancelar conservando identificador y datos.
- **Decisión:** cancelar = `UPDATE` del estado a `cancelada` y registro de `cancelada_en`. Se prohíbe `DELETE` sobre `reservas`.
- **Alternativas:** borrar la fila; mover la reserva a una tabla de histórico.
- **Consecuencias:** historial completo en una sola tabla. Las consultas de conflicto deben filtrar `estado = 'activa'`.

## D-11 · IDs consecutivos con `AUTOINCREMENT`, mostrados como `R-0001`

- **Contexto:** cada reserva debe ser identificable.
- **Decisión:** clave entera `AUTOINCREMENT`, presentada como `R-` más cuatro dígitos.
- **Alternativas:** UUID; ID compuesto por unidad y fecha.
- **Consecuencias:** IDs cortos y fáciles de escribir; nunca se reutilizan, ni siquiera tras cancelar.

## D-12 · Confirmación solo en acciones irreversibles; sin `--forzar`

- **Contexto:** `inicializar` borra datos y `cancelar` no se puede deshacer (no existe reactivar). Se había propuesto un parámetro `--forzar` para omitir la confirmación.
- **Decisión:** `inicializar` (si hay reservas) y `cancelar` piden confirmación (s/n); cualquier respuesta que no sea afirmativa se toma como "no". Se descarta `--forzar`. `reservar` y las consultas no preguntan.
- **Alternativas:** confirmar todo; no confirmar nada; mantener `--forzar`.
- **Motivo:** `--forzar` solo servía para automatizar, y las pruebas llaman al código directamente. Confirmar todo haría que el usuario responda sin leer.
- **Consecuencias:** se evitan cancelaciones por un ID mal escrito. Los tests de CLI deben simular la respuesta.

## D-13 · Verificar e insertar en una misma transacción

- **Contexto:** entre verificar disponibilidad e insertar podría colarse otra reserva.
- **Decisión:** usar `BEGIN IMMEDIATE` para la verificación y la inserción.
- **Alternativas:** verificar e insertar por separado.
- **Consecuencias:** no puede quedar guardada una superposición, incluso con dos procesos locales. No se busca soportar concurrencia distribuida (fuera de alcance).

## D-14 · Códigos de salida 0/1 además de los mensajes

- **Contexto:** la consigna no lo exige; los mensajes en español siempre se muestran.
- **Decisión:** 0 si la operación se completa; 1 si hay error o no se confirma.
- **Alternativas:** solo mensajes.
- **Consecuencias:** las pruebas de CLI pueden comprobar el resultado sin depender del texto exacto.

## D-15 · Agente: Claude Code con Opus 5.5 (esfuerzo alto) y aprobación humana

- **Contexto:** la consigna exige un agente que actúe sobre el repositorio con herramientas reales y documentar permisos y controles.
- **Decisión:** Claude Code 2.1.309; edición de archivos, ejecución de la app y commits requieren aprobación; `git push` está prohibido.
- **Alternativas:** auto-aceptar ediciones y revisar después; aprobar todo, incluso correr tests.
- **Consecuencias:** cada cambio pasa por revisión humana antes de aceptarse, lo que deja evidencia del control. El trabajo es más lento.

---

## Decisiones durante la construcción

<!-- Agregar aquí: D-16, D-17... con el commit o test que la respalda. -->

Las decisiones D-16 a D-20 surgieron de la **revisión de la especificación hecha por el agente** en la etapa 0, antes de escribir código. El agente señaló los huecos y el autor tomó cada decisión. Se reflejan en los supuestos S-13 a S-17, en RF-02, RF-05 y RF-06 y en los criterios CA-13 a CA-16 del README.

## D-16 · Reiniciar borra el archivo de la base; los IDs vuelven a `R-0001`

- **Contexto:** RF-06 dice que reiniciar borra las reservas, pero S-07 dice que los IDs nunca se reutilizan, y `CLAUDE.md` prohíbe `DELETE` sobre `reservas`.
- **Decisión:** `inicializar` borra el archivo de la base y lo crea de nuevo. Después de reiniciar, los IDs empiezan otra vez en `R-0001`. S-07 aplica dentro de una misma base (S-13).
- **Alternativas:** `DROP TABLE` y recrear el esquema; conservar la secuencia de IDs entre reinicios.
- **Consecuencias:** no se usa `DELETE` ni `DROP` sobre `reservas`. Un ID solo identifica una reserva dentro de una misma base: tras un reinicio, `R-0001` puede referirse a otra reserva.
- **Evidencia:** pendiente (CA-13).

## D-17 · `inicializar` sin reservas no pide confirmación

- **Contexto:** RF-06 y S-08 solo piden confirmación si ya existen reservas; no se decía qué informar en los demás casos.
- **Decisión:** si la base no existe, o existe pero no tiene reservas, `inicializar` la crea o la recrea sin preguntar e informa que se creó (S-14).
- **Alternativas:** pedir confirmación siempre que el archivo exista; negarse a recrear una base ya inicializada.
- **Consecuencias:** se pide confirmación solo cuando hay algo que perder.
- **Evidencia:** pendiente (CA-13).

## D-18 · `disponibilidad` devuelve 0 cuando la consulta se completa

- **Contexto:** S-10 (0 si la operación se completa, 1 si hay error) no aclaraba si una unidad ocupada o un intervalo en el pasado cuenta como error.
- **Decisión:** devuelve 0 con un resultado libre, ocupado o no reservable por estar en el pasado. Devuelve 1 solo con datos inválidos (unidad desconocida, fecha mal escrita, inicio igual o posterior al fin) o con la base no inicializada (S-15).
- **Alternativas:** devolver 1 cuando la unidad está ocupada o el intervalo no es reservable.
- **Consecuencias:** el código distingue "consulta mal hecha" de "respuesta negativa". Para saber si el intervalo está libre hay que leer el mensaje.
- **Evidencia:** pendiente (CA-14).

## D-19 · Orden, columnas y mensaje vacío de `listar`

- **Contexto:** RF-05 no definía orden ni columnas.
- **Decisión:** se ordena por inicio ascendente y, si empatan, por ID. Columnas: ID, unidad, solicitante, inicio, fin, estado. Sin reservas, muestra `No hay reservas.` y devuelve 0 (S-16).
- **Alternativas:** ordenar por ID; incluir `creada_en` y `cancelada_en` en la salida.
- **Consecuencias:** la salida se lee como una agenda cronológica y es estable para las pruebas.
- **Evidencia:** pendiente (CA-15).

## D-20 · Un archivo sin tablas cuenta como base no inicializada

- **Contexto:** S-09 contemplaba solo el caso de que la base no existiera. Además, `sqlite3.connect` crea un archivo vacío si no existe.
- **Decisión:** si el archivo existe pero no tiene las tablas, se trata como base no inicializada (S-17).
- **Alternativas:** crear el esquema automáticamente al abrir; mostrar un error técnico de SQLite.
- **Consecuencias:** el usuario recibe siempre el mismo mensaje ("ejecutá `inicializar`") y nunca una traza de SQLite.
- **Evidencia:** pendiente (CA-16).

## D-21 · Las rutas por defecto se calculan desde la raíz del proyecto

- **Contexto:** la especificación indica `datos/reservas.db` y `datos/inventario.csv`, pero no aclara desde qué carpeta se calculan. Surgió en la etapa 1; la propuso el agente y la aprobó el autor.
- **Decisión:** las dos rutas se calculan desde la carpeta que contiene el paquete `reservas/`, no desde la carpeta donde se ejecuta el comando. Si `RESERVAS_DB` es una ruta relativa, se toma desde la carpeta actual, como cualquier variable de entorno.
- **Alternativas:** calcular ambas rutas desde la carpeta actual.
- **Consecuencias:** ejecutar desde otra carpeta no crea una base suelta en otro lugar y el inventario se encuentra igual.
- **Evidencia:** `reservas/persistencia.py` (`RAIZ_PROYECTO`), test `tests/test_persistencia.py::test_ruta_base_por_defecto_es_datos_reservas_db`.

## D-22 · Interpretación del parámetro `ahora`

- **Contexto:** la especificación indica que `ahora` es un parámetro opcional, pero no aclara su zona horaria. Surgió en la etapa 2; la propuso el agente y la aprobó el autor.
- **Decisión:** internamente se trabaja con fechas sin zona, en hora de Buenos Aires. Un `ahora` sin zona se interpreta como hora de Buenos Aires; uno con zona se convierte a Buenos Aires. `creada_en` se guarda con esa hora.
- **Alternativas:** trabajar con fechas con zona en todo el código; aceptar solo `ahora` sin zona.
- **Consecuencias:** los tests pueden usar `datetime(2030, 11, 1, 9, 0)` sin zona, y un `ahora` en UTC no se compara mal.
- **Evidencia:** `reservas/reglas.py` (`_normalizar_ahora`), test `tests/test_crear_reserva.py::test_ahora_con_zona_horaria_se_convierte_a_buenos_aires`.

## D-23 · Las fechas no se recortan

- **Contexto:** S-06 indica recortar los espacios solo del solicitante; no dice nada sobre las fechas. Surgió en la etapa 2; el agente lo señaló y el autor decidió mantenerlo.
- **Decisión:** las fechas no se recortan. Una fecha con espacios al inicio o al final (ej. `" 2030-11-03 10:00"`) se rechaza por no respetar el formato.
- **Alternativas:** recortar las fechas igual que el solicitante.
- **Consecuencias:** el formato es estricto y coincide con RN-03 y S-02. El usuario tiene que escribir la fecha exacta.
- **Evidencia:** test `tests/test_crear_reserva.py::test_formato_de_fecha_invalido` (caso `" 2030-11-03 10:00"`).

## D-24 · Disponibilidad en el pasado y ocupada muestra ambas cosas

- **Contexto:** S-03 indica informar que un intervalo en el pasado no es reservable, pero no dice si además se listan las reservas que lo bloquean cuando también está ocupado. Surgió en la etapa 3; el agente lo planteó como pregunta y el autor decidió.
- **Decisión:** en `disponibilidad`, un intervalo que está en el pasado y ocupado muestra las dos cosas: que no es reservable por estar en el pasado y las reservas activas que lo bloquean. Se aplica en la CLI (etapa 5).
- **Alternativas:** mostrar solo "no reservable" y omitir las reservas que bloquean.
- **Consecuencias:** el usuario ve toda la información del intervalo. `consultar_disponibilidad` ya devuelve `en_pasado` y `conflictos` por separado, así que no hace falta cambiar la capa de reglas. Se refleja en la especificación como S-18 y CA-17.
- **Evidencia:** pendiente (CA-17, etapa 5).

## D-25 · Formato de ID de reserva aceptado

- **Contexto:** S-06 dice que el ID de reserva se acepta sin distinguir mayúsculas, pero no aclara si los ceros a la izquierda son obligatorios ni qué pasa con otros formatos. Surgió en la etapa 4; la propuso el agente y la aprobó el autor.
- **Decisión:** se acepta `R-` seguido de uno o más dígitos, sin distinguir mayúsculas y sin recortar espacios (como las fechas, D-23). `R-1` y `R-0001` se refieren a la misma reserva. Cualquier otro texto (`0001`, `R0001`, `X-0001`, `" R-0001"`) da el error "no es un ID de reserva válido".
- **Alternativas:** exigir exactamente el formato mostrado (cuatro dígitos o más); aceptar también el número solo (`1`).
- **Consecuencias:** el usuario puede escribir el ID corto; los mensajes siempre lo muestran como `R-0001`.
- **Evidencia:** `reservas/reglas.py` (`parsear_id_reserva`), tests `tests/test_cancelar_reserva.py::test_r_1_y_r_0001_son_la_misma_reserva` y `::test_id_mal_escrito_da_error_y_no_cambia_nada`.

## D-26 · No se cancelan reservas que ya empezaron

- **Contexto:** la especificación no decía si se puede cancelar una reserva cuyo horario ya empezó o terminó. Surgió en la etapa 4; el agente lo planteó como pregunta y el autor decidió.
- **Decisión:** si el inicio de la reserva es igual o anterior al momento actual, `cancelar` da error y no modifica nada (S-19, CA-18). Se usa el mismo criterio que para crear (S-03: inicio igual al "ahora" cuenta como pasado).
- **Alternativas:** permitir cancelar siempre; permitir cancelar solo las que no terminaron.
- **Consecuencias:** el historial de reservas ya empezadas o cumplidas no se altera. El orden de los errores es: inexistente, ya cancelada, ya empezó.
- **Evidencia:** test `tests/test_cancelar_reserva.py::test_cancelar_una_reserva_que_ya_empezo_da_error_y_no_cambia_nada` (justo al inicio, en curso y terminada) y `::test_cancelar_una_reserva_futura_se_permite`.

## D-27 · `listar` con filtros: unidad desconocida y resultados vacíos

- **Contexto:** RF-05 y S-16 no aclaraban qué pasa si `--unidad` no existe ni si `No hay reservas.` aplica también cuando un filtro no encuentra nada. Surgió en la etapa 5; la propuso el agente y la aprobó el autor.
- **Decisión:** `listar --unidad` con una unidad que no existe en el inventario da error y código 1 (RN-01). Un filtro válido sin resultados muestra `No hay reservas.` y devuelve 0.
- **Alternativas:** tratar la unidad desconocida como un filtro sin resultados; usar un mensaje distinto para "sin resultados con filtros".
- **Consecuencias:** un ID de unidad mal escrito no se confunde con "no hay reservas".
- **Evidencia:** tests `tests/test_cli.py::test_listar_con_unidad_desconocida_da_error` y `::test_listar_filtra_por_unidad_y_estado`.

## D-28 · Confirmación: sin distinguir mayúsculas ni espacios; sin entrada es "no"

- **Contexto:** S-08 enumera `s`, `si` y `sí` como afirmativos, pero no dice si importan las mayúsculas, los espacios o qué pasa si no hay entrada. Surgió en la etapa 5; la propuso el agente y la aprobó el autor.
- **Decisión:** se recortan los espacios y se ignoran las mayúsculas (`S`, ` Sí ` confirman). Si no hay entrada (fin de archivo o Ctrl+C), se toma como "no".
- **Alternativas:** aceptar solo las tres respuestas exactas en minúsculas.
- **Consecuencias:** cualquier otra respuesta sigue siendo "no" (por ejemplo `sii` o `no`), así que nunca se borra ni se cancela por error.
- **Evidencia:** tests `tests/test_cli.py::test_cancelar_con_respuesta_afirmativa`, `::test_cancelar_con_otra_respuesta_no_modifica_nada` y `::test_cancelar_sin_entrada_disponible_se_toma_como_no`.

## D-29 · `cancelar` valida antes de pedir confirmación

- **Contexto:** RF-04 dice que `cancelar` muestra la reserva y pide confirmación, pero no qué hacer si la reserva no se puede cancelar. Surgió en la etapa 5; la propuso el agente y la aprobó el autor.
- **Decisión:** si la reserva no existe, ya está cancelada o ya empezó, se muestra el error sin preguntar. Si se puede cancelar, se muestra y se pide confirmación; al confirmar, `cancelar_reserva` vuelve a validar dentro de la transacción.
- **Alternativas:** preguntar siempre y validar solo al confirmar.
- **Consecuencias:** no se pide confirmación en vano. La validación está en una sola función de reglas (`obtener_reserva_cancelable`), usada por la CLI y por `cancelar_reserva`.
- **Evidencia:** tests `tests/test_cli.py::test_cancelar_ya_cancelada_da_error_sin_preguntar`, `::test_cancelar_inexistente_da_error_sin_preguntar` y `::test_cancelar_reserva_que_ya_empezo_da_error_sin_preguntar`.

## D-30 · Errores de argumentos con código 1; `main()` con parámetros solo para pruebas

- **Contexto:** argparse sale con código 2 y mensajes en inglés ante argumentos inválidos; S-10 pide 1 para cualquier error y `CLAUDE.md` pide mensajes en español. Además, las pruebas de la CLI necesitan fijar el "ahora" y simular respuestas. Surgió en la etapa 5; la propuso el agente y la aprobó el autor.
- **Decisión:** los errores de argumentos devuelven 1 y los mensajes más comunes de argparse se traducen (los demás pueden quedar en inglés). `main(argv, ahora=None, leer_respuesta=input)` acepta `ahora` y `leer_respuesta` solo para las pruebas: la CLI real siempre usa la hora actual y la entrada estándar, y no hay forma de fijar el "ahora" desde argumentos ni variables de entorno (D-08).
- **Alternativas:** mantener el código 2 de argparse; probar la CLI solo con procesos aparte y hora real.
- **Consecuencias:** los criterios de la CLI se prueban con fecha fija. La traducción de argparse es parcial.
- **Evidencia:** tests `tests/test_cli.py::test_argumentos_invalidos_devuelven_1_con_mensaje_en_espanol` y el resto de `tests/test_cli.py`.
