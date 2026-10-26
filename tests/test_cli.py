import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from reservas.cli import main
from reservas.persistencia import abrir_base, obtener_reserva

AHORA = datetime(2030, 11, 1, 9, 0)
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

RESERVA_MIC01 = ["reservar", "MIC-01", "--solicitante", "Ana Prueba",
                 "--inicio", "2030-11-03 10:00", "--fin", "2030-11-03 11:00"]


@pytest.fixture(autouse=True)
def ruta_db(tmp_path, monkeypatch):
    """Toda la CLI apunta a una base temporal (nunca a datos/reservas.db)."""
    ruta = tmp_path / "cli.db"
    monkeypatch.setenv("RESERVAS_DB", str(ruta))
    return ruta


def sin_preguntas(texto):
    raise AssertionError(f"No se esperaba una confirmación: {texto!r}")


@pytest.fixture
def cli(capsys):
    """Ejecuta la CLI y devuelve (código, salida, errores)."""
    def ejecutar(*argv, respuestas=None, ahora=AHORA):
        if respuestas is None:
            leer = sin_preguntas
        else:
            pendientes = list(respuestas)
            leer = lambda texto: pendientes.pop(0)  # noqa: E731
        codigo = main(list(argv), ahora=ahora, leer_respuesta=leer)
        capturado = capsys.readouterr()
        return codigo, capturado.out, capturado.err
    return ejecutar


@pytest.fixture
def base(cli):
    codigo, _, _ = cli("inicializar")
    assert codigo == 0


def estado_de(ruta_db, reserva_id):
    conexion = abrir_base(ruta_db)
    try:
        return obtener_reserva(conexion, reserva_id)["estado"]
    finally:
        conexion.close()


def contar_reservas(ruta_db):
    conexion = abrir_base(ruta_db)
    try:
        return conexion.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
    finally:
        conexion.close()


# --- inicializar y unidades (RF-01, RF-06, CA-01, CA-13) ---

def test_inicializar_base_nueva_no_pregunta(cli, ruta_db):
    codigo, salida, _ = cli("inicializar")
    assert codigo == 0
    assert "Base de datos creada" in salida
    assert ruta_db.is_file()


def test_unidades_lista_exactamente_las_5(cli, base):
    codigo, salida, _ = cli("unidades")
    assert codigo == 0
    lineas = salida.strip().splitlines()
    assert lineas[0].split() == ["ID", "Equipo"]
    assert [linea.split()[0] for linea in lineas[1:]] == [
        "MIC-01", "MIC-02", "OSC-01", "MUL-01", "FUE-01"
    ]


def test_inicializar_con_reservas_y_respuesta_no_no_modifica_nada(cli, base, ruta_db):
    cli(*RESERVA_MIC01)

    codigo, salida, _ = cli("inicializar", respuestas=["n"])

    assert codigo == 1
    assert "1 reserva" in salida
    assert "se borrarán" in salida
    assert contar_reservas(ruta_db) == 1


def test_inicializar_con_reservas_y_respuesta_si_reinicia_los_ids(cli, base, ruta_db):
    cli(*RESERVA_MIC01)

    codigo, _, _ = cli("inicializar", respuestas=["s"])
    assert codigo == 0
    assert contar_reservas(ruta_db) == 0

    _, salida, _ = cli(*RESERVA_MIC01)
    assert "R-0001" in salida


def test_inicializar_base_sin_reservas_no_pregunta(cli, base):
    codigo, _, _ = cli("inicializar")
    assert codigo == 0


# --- base no inicializada (S-09, S-17, CA-16) ---

COMANDOS_CON_BASE = [
    ["unidades"],
    ["listar"],
    ["disponibilidad", "MIC-01", "--desde", "2030-11-03 10:00",
     "--hasta", "2030-11-03 11:00"],
    RESERVA_MIC01,
    ["cancelar", "R-0001"],
]


@pytest.mark.parametrize("argv", COMANDOS_CON_BASE)
def test_sin_base_indica_ejecutar_inicializar(cli, ruta_db, argv):
    codigo, _, errores = cli(*argv)
    assert codigo == 1
    assert "no está inicializada" in errores
    assert "inicializar" in errores
    assert not ruta_db.exists()


@pytest.mark.parametrize("argv", COMANDOS_CON_BASE)
def test_archivo_sin_tablas_se_trata_como_no_inicializado(cli, ruta_db, argv):
    ruta_db.touch()
    codigo, _, errores = cli(*argv)
    assert codigo == 1
    assert "no está inicializada" in errores


# --- reservar (RF-03, CA-12) ---

def test_reservar_muestra_el_id_nuevo(cli, base):
    codigo, salida, _ = cli(*RESERVA_MIC01)
    assert codigo == 0
    assert "Reserva creada: R-0001" in salida


def test_reservar_superpuesta_da_error(cli, base):
    cli(*RESERVA_MIC01)
    codigo, _, errores = cli("reservar", "MIC-01", "--solicitante", "Beto Prueba",
                             "--inicio", "2030-11-03 10:30", "--fin", "2030-11-03 11:30")
    assert codigo == 1
    assert "ya está reservada" in errores
    assert "R-0001" in errores


@pytest.mark.parametrize("argv", [
    ["reservar", "XYZ-99", "--solicitante", "Ana Prueba",
     "--inicio", "2030-11-03 10:00", "--fin", "2030-11-03 11:00"],
    ["reservar", "MIC-01", "--solicitante", "   ",
     "--inicio", "2030-11-03 10:00", "--fin", "2030-11-03 11:00"],
    ["reservar", "MIC-01", "--solicitante", "Ana Prueba",
     "--inicio", "2030-02-30 10:00", "--fin", "2030-11-03 11:00"],
    ["reservar", "MIC-01", "--solicitante", "Ana Prueba",
     "--inicio", "2030-10-31 10:00", "--fin", "2030-10-31 11:00"],
])
def test_reservar_invalida_da_error_sin_traza(cli, base, argv):
    codigo, _, errores = cli(*argv)
    assert codigo == 1
    assert errores.startswith("Error: ")
    assert "Traceback" not in errores


# --- disponibilidad (RF-02, S-15, S-18, CA-14, CA-17) ---

def disponibilidad(cli, desde, hasta, unidad="MIC-01", ahora=AHORA):
    return cli("disponibilidad", unidad, "--desde", desde, "--hasta", hasta, ahora=ahora)


def test_disponibilidad_libre(cli, base):
    codigo, salida, _ = disponibilidad(cli, "2030-11-03 10:00", "2030-11-03 11:00")
    assert codigo == 0
    assert "está libre" in salida


def test_disponibilidad_ocupada_lista_la_reserva_que_bloquea(cli, base):
    cli(*RESERVA_MIC01)
    codigo, salida, _ = disponibilidad(cli, "2030-11-03 10:30", "2030-11-03 11:30")
    assert codigo == 0
    assert "está ocupada" in salida
    assert "R-0001" in salida
    assert "está libre" not in salida


def test_disponibilidad_turno_consecutivo_libre(cli, base):
    cli(*RESERVA_MIC01)
    codigo, salida, _ = disponibilidad(cli, "2030-11-03 11:00", "2030-11-03 12:00")
    assert codigo == 0
    assert "está libre" in salida


def test_disponibilidad_en_el_pasado_no_es_reservable(cli, base):
    codigo, salida, _ = disponibilidad(cli, "2030-10-31 10:00", "2030-10-31 11:00")
    assert codigo == 0
    assert "no es reservable" in salida
    assert "está libre" not in salida


def test_disponibilidad_en_el_pasado_y_ocupada_muestra_ambas_cosas(cli, base, ruta_db):
    # CA-17 / D-24: la reserva se crea antes de su inicio y se consulta después.
    cli(*RESERVA_MIC01)
    codigo, salida, _ = disponibilidad(
        cli, "2030-11-03 10:30", "2030-11-03 11:30", ahora=datetime(2030, 11, 3, 12, 0)
    )
    assert codigo == 0
    assert "no es reservable" in salida
    assert "está ocupada" in salida
    assert "R-0001" in salida


@pytest.mark.parametrize("unidad, desde, hasta", [
    ("XYZ-99", "2030-11-03 10:00", "2030-11-03 11:00"),
    ("MIC-01", "2030/11/03 10:00", "2030-11-03 11:00"),
    ("MIC-01", "2030-11-03 11:00", "2030-11-03 10:00"),
])
def test_disponibilidad_con_datos_invalidos_da_error(cli, base, unidad, desde, hasta):
    codigo, _, errores = disponibilidad(cli, desde, hasta, unidad=unidad)
    assert codigo == 1
    assert errores.startswith("Error: ")


# --- cancelar (RF-04, S-08, S-19, CA-07, CA-08, CA-11, CA-18) ---

@pytest.mark.parametrize("respuesta", ["s", "si", "sí", "S", " Sí "])
def test_cancelar_con_respuesta_afirmativa(cli, base, ruta_db, respuesta):
    cli(*RESERVA_MIC01)
    codigo, salida, _ = cli("cancelar", "R-0001", respuestas=[respuesta])
    assert codigo == 0
    assert "R-0001" in salida
    assert "Ana Prueba" in salida
    assert "cancelada" in salida
    assert estado_de(ruta_db, 1) == "cancelada"


@pytest.mark.parametrize("respuesta", ["n", "no", "", "x", "sii"])
def test_cancelar_con_otra_respuesta_no_modifica_nada(cli, base, ruta_db, respuesta):
    cli(*RESERVA_MIC01)
    codigo, salida, _ = cli("cancelar", "R-0001", respuestas=[respuesta])
    assert codigo == 1
    assert "No se modificó" in salida
    assert estado_de(ruta_db, 1) == "activa"


def test_cancelar_ya_cancelada_da_error_sin_preguntar(cli, base):
    cli(*RESERVA_MIC01)
    cli("cancelar", "R-0001", respuestas=["s"])
    codigo, _, errores = cli("cancelar", "R-0001")
    assert codigo == 1
    assert "ya está cancelada" in errores


def test_cancelar_inexistente_da_error_sin_preguntar(cli, base):
    codigo, _, errores = cli("cancelar", "R-0099")
    assert codigo == 1
    assert "No existe la reserva R-0099" in errores


def test_cancelar_reserva_que_ya_empezo_da_error_sin_preguntar(cli, base, ruta_db):
    cli(*RESERVA_MIC01)
    codigo, _, errores = cli("cancelar", "R-0001", ahora=datetime(2030, 11, 3, 10, 30))
    assert codigo == 1
    assert "ya empezó" in errores
    assert estado_de(ruta_db, 1) == "activa"


def test_cancelar_sin_entrada_disponible_se_toma_como_no(cli, base, ruta_db):
    def sin_entrada(texto):
        raise EOFError
    cli(*RESERVA_MIC01)
    codigo = main(["cancelar", "R-0001"], ahora=AHORA, leer_respuesta=sin_entrada)
    assert codigo == 1
    assert estado_de(ruta_db, 1) == "activa"


# --- listar (RF-05, S-16, CA-15) ---

def test_listar_sin_reservas(cli, base):
    codigo, salida, _ = cli("listar")
    assert codigo == 0
    assert salida.strip() == "No hay reservas."


def test_listar_ordena_por_inicio_y_muestra_las_columnas(cli, base):
    cli("reservar", "OSC-01", "--solicitante", "Beto Prueba",
        "--inicio", "2030-11-04 08:00", "--fin", "2030-11-04 09:00")
    cli(*RESERVA_MIC01)
    cli("reservar", "MIC-02", "--solicitante", "Caro Prueba",
        "--inicio", "2030-11-03 10:00", "--fin", "2030-11-03 11:00")

    codigo, salida, _ = cli("listar")

    assert codigo == 0
    lineas = salida.strip().splitlines()
    assert lineas[0].split() == ["ID", "Unidad", "Solicitante", "Inicio", "Fin", "Estado"]
    # Por inicio; R-0002 y R-0003 empatan en inicio y se ordenan por ID.
    assert [linea.split()[0] for linea in lineas[1:]] == ["R-0002", "R-0003", "R-0001"]


def test_listar_filtra_por_unidad_y_estado(cli, base):
    cli(*RESERVA_MIC01)
    cli("reservar", "MIC-02", "--solicitante", "Beto Prueba",
        "--inicio", "2030-11-03 10:00", "--fin", "2030-11-03 11:00")
    cli("cancelar", "R-0001", respuestas=["s"])

    _, salida, _ = cli("listar", "--unidad", "mic-01", "--estado", "cancelada")
    assert [linea.split()[0] for linea in salida.strip().splitlines()[1:]] == ["R-0001"]

    _, salida, _ = cli("listar", "--estado", "activa")
    assert [linea.split()[0] for linea in salida.strip().splitlines()[1:]] == ["R-0002"]


def test_listar_con_unidad_desconocida_da_error(cli, base):
    codigo, _, errores = cli("listar", "--unidad", "XYZ-99")
    assert codigo == 1
    assert "no existe en el inventario" in errores


# --- argumentos inválidos (S-10, CA-12) ---

@pytest.mark.parametrize("argv", [
    [],
    ["comando-inexistente"],
    ["reservar", "MIC-01"],
    ["listar", "--estado", "pendiente"],
])
def test_argumentos_invalidos_devuelven_1_con_mensaje_en_espanol(cli, argv):
    codigo, _, errores = cli(*argv)
    assert codigo == 1
    assert "Error: " in errores
    assert "uso: " in errores


# --- De punta a punta: `python -m reservas` en un proceso aparte ---
# Excepción aprobada a la regla de CLAUDE.md "los tests pasan siempre una
# fecha fija": la CLI no permite fijar el "ahora", así que estos tests usan la
# hora real. Por eso usan fechas de 2099 (como los tests de ahora=None de la
# etapa 2) y no de 2030, que dejarían de ser futuras en noviembre de 2030.

RESERVA_MIC01_2099 = ["reservar", "MIC-01", "--solicitante", "Ana Prueba",
                      "--inicio", "2099-11-03 10:00", "--fin", "2099-11-03 11:00"]


def ejecutar_proceso(ruta_db, *argv, entrada=None):
    entorno = {**os.environ, "RESERVAS_DB": str(ruta_db)}
    return subprocess.run(
        [sys.executable, "-m", "reservas", *argv],
        cwd=RAIZ_PROYECTO, env=entorno, input=entrada,
        capture_output=True, text=True, timeout=30,
    )


def test_punta_a_punta_reservar_consultar_y_listar(ruta_db):
    assert ejecutar_proceso(ruta_db, "inicializar").returncode == 0

    reserva = ejecutar_proceso(ruta_db, *RESERVA_MIC01_2099)
    assert reserva.returncode == 0
    assert "Reserva creada: R-0001" in reserva.stdout

    choque = ejecutar_proceso(ruta_db, "reservar", "MIC-01", "--solicitante", "Beto Prueba",
                              "--inicio", "2099-11-03 10:30", "--fin", "2099-11-03 11:30")
    assert choque.returncode == 1
    assert "ya está reservada" in choque.stderr
    assert "Traceback" not in choque.stderr

    consecutiva = ejecutar_proceso(ruta_db, "disponibilidad", "MIC-01",
                                   "--desde", "2099-11-03 11:00", "--hasta", "2099-11-03 12:00")
    assert consecutiva.returncode == 0
    assert "está libre" in consecutiva.stdout

    listado = ejecutar_proceso(ruta_db, "listar")
    assert listado.returncode == 0
    assert "R-0001" in listado.stdout
    assert "activa" in listado.stdout


def test_punta_a_punta_cancelar_con_confirmacion(ruta_db):
    ejecutar_proceso(ruta_db, "inicializar")
    ejecutar_proceso(ruta_db, *RESERVA_MIC01_2099)

    rechazo = ejecutar_proceso(ruta_db, "cancelar", "R-0001", entrada="n\n")
    assert rechazo.returncode == 1
    assert "No se modificó" in rechazo.stdout

    cancelacion = ejecutar_proceso(ruta_db, "cancelar", "r-0001", entrada="s\n")
    assert cancelacion.returncode == 0
    assert "Reserva R-0001 cancelada." in cancelacion.stdout

    listado = ejecutar_proceso(ruta_db, "listar", "--estado", "cancelada")
    assert "R-0001" in listado.stdout

    otra_vez = ejecutar_proceso(ruta_db, "cancelar", "R-0001")
    assert otra_vez.returncode == 1
    assert "ya está cancelada" in otra_vez.stderr
