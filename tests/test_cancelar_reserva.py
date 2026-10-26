from datetime import datetime

import pytest

from reservas.errores import (
    ErrorReservaNoEncontrada,
    ErrorReservaYaCancelada,
    ErrorValidacion,
)
from reservas.persistencia import obtener_reserva
from reservas.reglas import (
    cancelar_reserva,
    consultar_disponibilidad,
    crear_reserva,
    formatear_id_reserva,
)

AHORA_RESERVA = datetime(2030, 11, 1, 9, 0)
AHORA_CANCELACION = datetime(2030, 11, 2, 8, 30)
INICIO = "2030-11-03 10:00"
FIN = "2030-11-03 11:00"


def todas_las_reservas(conexion):
    """Copia completa de la tabla, para comprobar que no cambió nada."""
    return [tuple(fila) for fila in conexion.execute("SELECT * FROM reservas ORDER BY id")]


@pytest.fixture
def reserva_activa(conexion):
    """Base con R-0001: MIC-01 del 2030-11-03 de 10:00 a 11:00, activa."""
    crear_reserva(conexion, "MIC-01", "Ana Prueba", INICIO, FIN, ahora=AHORA_RESERVA)
    return conexion


# --- Cancelación válida (CA-07, RN-11) ---

def test_cancelar_conserva_el_registro_y_sus_datos(reserva_activa):
    antes = obtener_reserva(reserva_activa, 1)

    cancelar_reserva(reserva_activa, "R-0001", ahora=AHORA_CANCELACION)

    despues = obtener_reserva(reserva_activa, 1)
    assert despues is not None
    for campo in ("id", "unidad_id", "solicitante", "inicio", "fin", "creada_en"):
        assert despues[campo] == antes[campo]
    assert despues["estado"] == "cancelada"
    assert despues["cancelada_en"] == "2030-11-02 08:30:00"
    assert len(todas_las_reservas(reserva_activa)) == 1


def test_cancelar_devuelve_la_reserva_actualizada(reserva_activa):
    reserva = cancelar_reserva(reserva_activa, "R-0001", ahora=AHORA_CANCELACION)
    assert formatear_id_reserva(reserva["id"]) == "R-0001"
    assert reserva["estado"] == "cancelada"


def test_cancelar_acepta_el_id_sin_distinguir_mayusculas(reserva_activa):
    cancelar_reserva(reserva_activa, "r-0001", ahora=AHORA_CANCELACION)
    assert obtener_reserva(reserva_activa, 1)["estado"] == "cancelada"


def test_r_1_y_r_0001_son_la_misma_reserva(reserva_activa):
    # D-25: los ceros a la izquierda son opcionales.
    cancelar_reserva(reserva_activa, "R-1", ahora=AHORA_CANCELACION)
    assert obtener_reserva(reserva_activa, 1)["estado"] == "cancelada"

    with pytest.raises(ErrorReservaYaCancelada, match="R-0001"):
        cancelar_reserva(reserva_activa, "R-0001", ahora=AHORA_CANCELACION)


def test_cancelar_una_reserva_futura_se_permite(reserva_activa):
    # Un minuto antes del inicio (2030-11-03 10:00).
    cancelar_reserva(reserva_activa, "R-0001", ahora=datetime(2030, 11, 3, 9, 59))
    assert obtener_reserva(reserva_activa, 1)["estado"] == "cancelada"


def test_cancelar_libera_el_horario(reserva_activa):
    cancelar_reserva(reserva_activa, "R-0001", ahora=AHORA_CANCELACION)

    disponibilidad = consultar_disponibilidad(
        reserva_activa, "MIC-01", INICIO, FIN, ahora=AHORA_CANCELACION
    )
    assert disponibilidad.reservable
    nueva = crear_reserva(
        reserva_activa, "MIC-01", "Beto Prueba", INICIO, FIN, ahora=AHORA_CANCELACION
    )
    # El ID de la cancelada no se reutiliza (S-07).
    assert formatear_id_reserva(nueva) == "R-0002"
    assert obtener_reserva(reserva_activa, 1)["estado"] == "cancelada"
    assert obtener_reserva(reserva_activa, 2)["estado"] == "activa"


def test_cancelar_solo_afecta_a_la_reserva_indicada(reserva_activa):
    crear_reserva(
        reserva_activa, "MIC-02", "Beto Prueba", INICIO, FIN, ahora=AHORA_RESERVA
    )
    otra_antes = tuple(obtener_reserva(reserva_activa, 2))

    cancelar_reserva(reserva_activa, "R-0001", ahora=AHORA_CANCELACION)

    assert tuple(obtener_reserva(reserva_activa, 2)) == otra_antes


def test_cancelar_usa_update_y_nunca_delete(reserva_activa):
    sentencias = []
    reserva_activa.set_trace_callback(sentencias.append)

    cancelar_reserva(reserva_activa, "R-0001", ahora=AHORA_CANCELACION)
    reserva_activa.set_trace_callback(None)

    assert not any(s.upper().startswith("DELETE") for s in sentencias)
    assert any(s.startswith("UPDATE reservas") for s in sentencias)
    assert sentencias[0] == "BEGIN IMMEDIATE"
    assert sentencias[-1] == "COMMIT"


# --- Errores (CA-08, RN-12): no modifican nada ---

def test_doble_cancelacion_da_error_y_no_cambia_nada(reserva_activa):
    cancelar_reserva(reserva_activa, "R-0001", ahora=AHORA_CANCELACION)
    antes = todas_las_reservas(reserva_activa)

    with pytest.raises(ErrorReservaYaCancelada, match="R-0001 ya está cancelada"):
        cancelar_reserva(reserva_activa, "R-0001", ahora=datetime(2030, 11, 2, 9, 0))

    # cancelada_en conserva la fecha de la primera cancelación.
    assert todas_las_reservas(reserva_activa) == antes
    assert not reserva_activa.in_transaction


@pytest.mark.parametrize("ahora", [
    datetime(2030, 11, 3, 10, 0),    # justo al inicio
    datetime(2030, 11, 3, 10, 30),   # en curso
    datetime(2030, 11, 3, 12, 0),    # ya terminó
])
def test_cancelar_una_reserva_que_ya_empezo_da_error_y_no_cambia_nada(
    reserva_activa, ahora
):
    # D-26 / S-19 / CA-18.
    antes = todas_las_reservas(reserva_activa)

    with pytest.raises(ErrorValidacion, match="R-0001: ya empezó"):
        cancelar_reserva(reserva_activa, "R-0001", ahora=ahora)

    assert todas_las_reservas(reserva_activa) == antes
    assert not reserva_activa.in_transaction


def test_cancelar_reserva_inexistente_da_error_y_no_cambia_nada(reserva_activa):
    antes = todas_las_reservas(reserva_activa)

    with pytest.raises(ErrorReservaNoEncontrada, match="No existe la reserva R-0099"):
        cancelar_reserva(reserva_activa, "R-0099", ahora=AHORA_CANCELACION)

    assert todas_las_reservas(reserva_activa) == antes
    assert not reserva_activa.in_transaction


@pytest.mark.parametrize("texto", ["", "0001", "1", "R0001", "X-0001", "R-", "R-abc", " R-0001"])
def test_id_mal_escrito_da_error_y_no_cambia_nada(reserva_activa, texto):
    antes = todas_las_reservas(reserva_activa)

    with pytest.raises(ErrorReservaNoEncontrada, match="no es un ID de reserva válido"):
        cancelar_reserva(reserva_activa, texto, ahora=AHORA_CANCELACION)

    assert todas_las_reservas(reserva_activa) == antes
