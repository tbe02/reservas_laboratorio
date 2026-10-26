from datetime import datetime, timezone

import pytest

from reservas.errores import ErrorValidacion
from reservas.persistencia import obtener_reserva
from reservas.reglas import crear_reserva, formatear_id_reserva

AHORA = datetime(2030, 11, 1, 9, 0)


def contar_reservas(conexion):
    return conexion.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]


def crear(conexion, unidad="MIC-01", solicitante="Ana Prueba",
          inicio="2030-11-03 10:00", fin="2030-11-03 11:00", ahora=AHORA):
    return crear_reserva(conexion, unidad, solicitante, inicio, fin, ahora=ahora)


# --- Creación válida (CA-02) ---

def test_reserva_valida_se_crea_activa_con_sus_datos(conexion):
    reserva_id = crear(conexion)

    reserva = obtener_reserva(conexion, reserva_id)
    assert reserva["unidad_id"] == "MIC-01"
    assert reserva["solicitante"] == "Ana Prueba"
    assert reserva["inicio"] == "2030-11-03 10:00"
    assert reserva["fin"] == "2030-11-03 11:00"
    assert reserva["estado"] == "activa"
    assert reserva["creada_en"] == "2030-11-01 09:00:00"
    assert reserva["cancelada_en"] is None


def test_cada_reserva_recibe_un_id_nuevo(conexion):
    primera = crear(conexion, unidad="MIC-01")
    segunda = crear(conexion, unidad="OSC-01")

    assert formatear_id_reserva(primera) == "R-0001"
    assert formatear_id_reserva(segunda) == "R-0002"


def test_unidad_sin_distinguir_mayusculas_y_solicitante_recortado(conexion):
    reserva_id = crear(conexion, unidad="mic-01", solicitante="  Ana Prueba  ")

    reserva = obtener_reserva(conexion, reserva_id)
    assert reserva["unidad_id"] == "MIC-01"
    assert reserva["solicitante"] == "Ana Prueba"


def test_reserva_que_cruza_la_medianoche_es_valida(conexion):
    reserva_id = crear(conexion, inicio="2030-11-03 22:00", fin="2030-11-04 02:00")
    assert obtener_reserva(conexion, reserva_id)["estado"] == "activa"


def test_ahora_con_zona_horaria_se_convierte_a_buenos_aires(conexion):
    # 13:00 UTC son las 10:00 en Buenos Aires (UTC-3).
    ahora_utc = datetime(2030, 11, 3, 13, 0, tzinfo=timezone.utc)

    with pytest.raises(ErrorValidacion):
        crear(conexion, inicio="2030-11-03 10:00", ahora=ahora_utc)
    reserva_id = crear(conexion, inicio="2030-11-03 10:01", ahora=ahora_utc)
    assert obtener_reserva(conexion, reserva_id)["creada_en"] == "2030-11-03 10:00:00"


# --- Casos inválidos (CA-06): todos lanzan ErrorValidacion y no guardan nada ---

def test_unidad_desconocida(conexion):
    with pytest.raises(ErrorValidacion, match="no existe en el inventario"):
        crear(conexion, unidad="XYZ-99")
    assert contar_reservas(conexion) == 0


@pytest.mark.parametrize("solicitante", ["", " ", "   \t  "])
def test_solicitante_vacio_o_solo_espacios(conexion, solicitante):
    with pytest.raises(ErrorValidacion, match="solicitante"):
        crear(conexion, solicitante=solicitante)
    assert contar_reservas(conexion) == 0


@pytest.mark.parametrize("fecha", [
    "",
    "mañana",
    "2030-11-03",
    "2030/11/03 10:00",
    "03-11-2030 10:00",
    "2030-11-03T10:00",
    "2030-11-03 10:00:00",
    "2030-1-3 10:00",
    "2030-11-03 9:00",
    " 2030-11-03 10:00",
])
@pytest.mark.parametrize("campo", ["inicio", "fin"])
def test_formato_de_fecha_invalido(conexion, campo, fecha):
    with pytest.raises(ErrorValidacion, match="formato"):
        crear(conexion, **{campo: fecha})
    assert contar_reservas(conexion) == 0


@pytest.mark.parametrize("fecha", [
    "2030-02-30 10:00",
    "2031-02-29 10:00",
    "2030-13-01 10:00",
    "2030-11-31 10:00",
    "2030-11-03 24:00",
    "2030-11-03 10:60",
])
@pytest.mark.parametrize("campo", ["inicio", "fin"])
def test_fecha_inexistente(conexion, campo, fecha):
    with pytest.raises(ErrorValidacion, match="no es una fecha válida"):
        crear(conexion, **{campo: fecha})
    assert contar_reservas(conexion) == 0


def test_inicio_igual_al_fin(conexion):
    with pytest.raises(ErrorValidacion, match="anterior al fin"):
        crear(conexion, inicio="2030-11-03 10:00", fin="2030-11-03 10:00")
    assert contar_reservas(conexion) == 0


def test_inicio_posterior_al_fin(conexion):
    with pytest.raises(ErrorValidacion, match="anterior al fin"):
        crear(conexion, inicio="2030-11-03 11:00", fin="2030-11-03 10:00")
    assert contar_reservas(conexion) == 0


def test_inicio_en_el_pasado(conexion):
    with pytest.raises(ErrorValidacion, match="posterior al momento actual"):
        crear(conexion, inicio="2030-10-31 10:00", fin="2030-10-31 11:00")
    assert contar_reservas(conexion) == 0


def test_inicio_igual_al_momento_actual(conexion):
    with pytest.raises(ErrorValidacion, match="posterior al momento actual"):
        crear(conexion, inicio="2030-11-01 09:00", fin="2030-11-01 10:00")
    assert contar_reservas(conexion) == 0


def test_inicio_un_minuto_despues_del_momento_actual_es_valido(conexion):
    reserva_id = crear(conexion, inicio="2030-11-01 09:01", fin="2030-11-01 10:00")
    assert obtener_reserva(conexion, reserva_id)["estado"] == "activa"


# --- Camino ahora=None (hora real) ---
# Excepción aprobada a la regla de CLAUDE.md "los tests pasan siempre una
# fecha fija": estos dos tests usan la hora real, pero con fechas tan lejanas
# (2000 y 2099) que el resultado no depende del momento exacto en que corren.

def test_ahora_none_acepta_una_reserva_en_2099(conexion):
    reserva_id = crear(
        conexion, inicio="2099-11-03 10:00", fin="2099-11-03 11:00", ahora=None
    )
    assert obtener_reserva(conexion, reserva_id)["estado"] == "activa"


def test_ahora_none_rechaza_una_reserva_en_2000(conexion):
    with pytest.raises(ErrorValidacion, match="posterior al momento actual"):
        crear(conexion, inicio="2000-11-03 10:00", fin="2000-11-03 11:00", ahora=None)
    assert contar_reservas(conexion) == 0
