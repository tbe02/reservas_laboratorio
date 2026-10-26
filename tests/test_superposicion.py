from datetime import datetime

import pytest

from reservas.errores import ErrorReservas, ErrorSuperposicion, ErrorValidacion
from reservas.reglas import (
    cancelar_reserva,
    consultar_disponibilidad,
    crear_reserva,
    formatear_id_reserva,
)

AHORA = datetime(2030, 11, 1, 9, 0)
DIA = "2030-11-03"


def contar_reservas(conexion):
    return conexion.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]


def reservar(conexion, unidad, desde, hasta, solicitante="Ana Prueba"):
    return crear_reserva(
        conexion, unidad, solicitante, f"{DIA} {desde}", f"{DIA} {hasta}",
        ahora=AHORA,
    )


def disponibilidad(conexion, unidad, desde, hasta):
    return consultar_disponibilidad(
        conexion, unidad, f"{DIA} {desde}", f"{DIA} {hasta}", ahora=AHORA
    )


@pytest.fixture
def mic01_ocupado(conexion):
    """Base con MIC-01 reservado el 2030-11-03 de 10:00 a 11:00."""
    reservar(conexion, "MIC-01", "10:00", "11:00", solicitante="Beto Prueba")
    return conexion


# --- Ejemplo de la consigna (CA-03, CA-04, CA-05) ---

def test_consigna_rechaza_mic01_de_10_30_a_11_30(mic01_ocupado):
    with pytest.raises(ErrorSuperposicion):
        reservar(mic01_ocupado, "MIC-01", "10:30", "11:30")
    assert contar_reservas(mic01_ocupado) == 1


def test_consigna_permite_mic01_de_11_a_12(mic01_ocupado):
    reserva_id = reservar(mic01_ocupado, "MIC-01", "11:00", "12:00")
    assert formatear_id_reserva(reserva_id) == "R-0002"


def test_consigna_permite_mic02_de_10_a_11_con_mic01_ocupado(mic01_ocupado):
    reserva_id = reservar(mic01_ocupado, "MIC-02", "10:00", "11:00")
    assert formatear_id_reserva(reserva_id) == "R-0002"


# --- Otros casos de superposición (RN-07, RN-08, RN-09) ---

@pytest.mark.parametrize("unidad, desde, hasta", [
    ("MIC-01", "10:00", "11:00"),   # idéntico
    ("MIC-01", "09:30", "10:30"),   # pisa el comienzo
    ("MIC-01", "10:15", "10:45"),   # contenido
    ("MIC-01", "09:00", "12:00"),   # contiene
    ("MIC-01", "10:59", "11:30"),   # un minuto de superposición
    ("mic-01", "10:30", "11:30"),   # unidad en minúsculas
])
def test_superposiciones_se_rechazan(mic01_ocupado, unidad, desde, hasta):
    with pytest.raises(ErrorSuperposicion):
        reservar(mic01_ocupado, unidad, desde, hasta)
    assert contar_reservas(mic01_ocupado) == 1


def test_turno_consecutivo_anterior_se_permite(mic01_ocupado):
    reservar(mic01_ocupado, "MIC-01", "09:00", "10:00")
    assert contar_reservas(mic01_ocupado) == 2


def test_error_de_superposicion_indica_la_reserva_que_bloquea(mic01_ocupado):
    with pytest.raises(ErrorSuperposicion, match="R-0001") as error:
        reservar(mic01_ocupado, "MIC-01", "10:30", "11:30")
    assert [c["id"] for c in error.value.conflictos] == [1]


def test_reserva_cancelada_no_bloquea(mic01_ocupado):
    cancelar_reserva(mic01_ocupado, "R-0001", ahora=AHORA)
    assert disponibilidad(mic01_ocupado, "MIC-01", "10:30", "11:30").reservable
    reservar(mic01_ocupado, "MIC-01", "10:30", "11:30")
    assert contar_reservas(mic01_ocupado) == 2


# --- Consulta de disponibilidad (RF-02, S-03) ---

def test_disponibilidad_libre(mic01_ocupado):
    resultado = disponibilidad(mic01_ocupado, "MIC-01", "11:00", "12:00")
    assert resultado.libre
    assert resultado.reservable
    assert resultado.conflictos == []


def test_disponibilidad_ocupada_lista_las_reservas_que_bloquean(mic01_ocupado):
    resultado = disponibilidad(mic01_ocupado, "MIC-01", "10:30", "11:30")
    assert not resultado.libre
    assert not resultado.reservable
    assert [formatear_id_reserva(c["id"]) for c in resultado.conflictos] == ["R-0001"]
    assert resultado.conflictos[0]["solicitante"] == "Beto Prueba"


def test_disponibilidad_lista_todas_las_reservas_que_bloquean(mic01_ocupado):
    reservar(mic01_ocupado, "MIC-01", "11:00", "12:00")
    resultado = disponibilidad(mic01_ocupado, "MIC-01", "10:30", "11:30")
    assert [c["id"] for c in resultado.conflictos] == [1, 2]


def test_disponibilidad_en_el_pasado_no_es_reservable(conexion):
    resultado = consultar_disponibilidad(
        conexion, "MIC-01", "2030-10-31 10:00", "2030-10-31 11:00", ahora=AHORA
    )
    assert resultado.en_pasado
    assert resultado.libre
    assert not resultado.reservable


def test_disponibilidad_no_modifica_la_base(mic01_ocupado):
    disponibilidad(mic01_ocupado, "MIC-01", "11:00", "12:00")
    assert contar_reservas(mic01_ocupado) == 1


# --- disponibilidad coincide con crear_reserva (CA-09, RN-10) ---

@pytest.mark.parametrize("unidad, inicio, fin, esperado", [
    ("MIC-01", f"{DIA} 10:30", f"{DIA} 11:30", False),   # CA-03
    ("MIC-01", f"{DIA} 11:00", f"{DIA} 12:00", True),    # CA-04
    ("MIC-02", f"{DIA} 10:00", f"{DIA} 11:00", True),    # CA-05
    ("MIC-01", f"{DIA} 09:00", f"{DIA} 10:00", True),    # consecutivo anterior
    ("MIC-01", f"{DIA} 10:15", f"{DIA} 10:45", False),   # contenido
    ("MIC-01", f"{DIA} 09:00", f"{DIA} 12:00", False),   # contiene
    ("mic-01", f"{DIA} 10:30", f"{DIA} 11:30", False),   # minúsculas
    ("MIC-01", "2030-10-31 10:00", "2030-10-31 11:00", False),  # pasado (CA-06)
])
def test_disponibilidad_coincide_con_crear_reserva(
    mic01_ocupado, unidad, inicio, fin, esperado
):
    resultado = consultar_disponibilidad(
        mic01_ocupado, unidad, inicio, fin, ahora=AHORA
    )
    try:
        crear_reserva(mic01_ocupado, unidad, "Ana Prueba", inicio, fin, ahora=AHORA)
        creada = True
    except ErrorReservas:
        creada = False

    assert resultado.reservable == esperado
    assert creada == esperado


@pytest.mark.parametrize("unidad, inicio, fin", [
    ("XYZ-99", f"{DIA} 10:00", f"{DIA} 11:00"),       # unidad desconocida
    ("MIC-01", "2030/11/03 10:00", f"{DIA} 11:00"),   # formato inválido
    ("MIC-01", "2030-02-30 10:00", f"{DIA} 11:00"),   # fecha inexistente
    ("MIC-01", f"{DIA} 11:00", f"{DIA} 11:00"),       # inicio igual al fin
    ("MIC-01", f"{DIA} 12:00", f"{DIA} 11:00"),       # inicio posterior al fin
])
def test_datos_invalidos_dan_error_en_ambas(mic01_ocupado, unidad, inicio, fin):
    with pytest.raises(ErrorValidacion):
        consultar_disponibilidad(mic01_ocupado, unidad, inicio, fin, ahora=AHORA)
    with pytest.raises(ErrorValidacion):
        crear_reserva(mic01_ocupado, unidad, "Ana Prueba", inicio, fin, ahora=AHORA)
    assert contar_reservas(mic01_ocupado) == 1


# --- Transacción (D-13) ---

def test_verificacion_e_insercion_ocurren_en_una_transaccion_inmediata(conexion):
    sentencias = []
    conexion.set_trace_callback(sentencias.append)

    reservar(conexion, "MIC-01", "10:00", "11:00")
    conexion.set_trace_callback(None)

    def posicion(prefijo):
        return next(i for i, s in enumerate(sentencias) if s.startswith(prefijo))

    assert (
        posicion("BEGIN IMMEDIATE")
        < posicion("SELECT * FROM reservas")
        < posicion("INSERT INTO reservas")
        < posicion("COMMIT")
    )


@pytest.mark.parametrize("desde, hasta, solicitante, error", [
    ("10:30", "11:30", "Ana Prueba", ErrorSuperposicion),
    ("11:00", "12:00", "   ", ErrorValidacion),
])
def test_un_rechazo_no_deja_la_transaccion_abierta(
    mic01_ocupado, desde, hasta, solicitante, error
):
    with pytest.raises(error):
        reservar(mic01_ocupado, "MIC-01", desde, hasta, solicitante=solicitante)
    assert not mic01_ocupado.in_transaction
    assert contar_reservas(mic01_ocupado) == 1
