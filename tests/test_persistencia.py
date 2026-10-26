from datetime import datetime

import pytest

from reservas.errores import ErrorBaseNoInicializada
from reservas.persistencia import (
    RUTA_BASE_POR_DEFECTO,
    abrir_base,
    crear_base,
    leer_inventario,
    listar_unidades,
    obtener_reserva,
    ruta_base,
)
from reservas.reglas import (
    cancelar_reserva,
    consultar_disponibilidad,
    crear_reserva,
    formatear_id_reserva,
)

INVENTARIO_ESPERADO = [
    ("MIC-01", "Microscopio digital"),
    ("MIC-02", "Microscopio digital"),
    ("OSC-01", "Osciloscopio"),
    ("MUL-01", "Multímetro"),
    ("FUE-01", "Fuente de alimentación"),
]


def test_leer_inventario_devuelve_las_5_unidades_del_csv():
    assert leer_inventario() == INVENTARIO_ESPERADO


def test_crear_base_carga_exactamente_las_5_unidades(conexion):
    unidades = [(fila["id"], fila["equipo"]) for fila in listar_unidades(conexion)]
    assert unidades == INVENTARIO_ESPERADO


def test_crear_base_empieza_sin_reservas(conexion):
    assert conexion.execute("SELECT COUNT(*) FROM reservas").fetchone()[0] == 0


def test_crear_base_sobre_base_existente_la_recrea_desde_cero(ruta_db, conexion):
    conexion.execute(
        "INSERT INTO reservas (unidad_id, solicitante, inicio, fin, creada_en) "
        "VALUES ('MIC-01', 'Ana Prueba', '2030-11-03 10:00', '2030-11-03 11:00', "
        "'2030-11-01 09:00:00')"
    )
    conexion.close()

    crear_base(ruta_db)

    nueva = abrir_base(ruta_db)
    try:
        assert nueva.execute("SELECT COUNT(*) FROM reservas").fetchone()[0] == 0
        assert len(listar_unidades(nueva)) == 5
        cursor = nueva.execute(
            "INSERT INTO reservas (unidad_id, solicitante, inicio, fin, creada_en) "
            "VALUES ('MIC-01', 'Ana Prueba', '2030-11-03 10:00', "
            "'2030-11-03 11:00', '2030-11-01 09:00:00')"
        )
        assert cursor.lastrowid == 1
    finally:
        nueva.close()


def test_abrir_base_inexistente_falla_sin_crear_el_archivo(ruta_db):
    with pytest.raises(ErrorBaseNoInicializada):
        abrir_base(ruta_db)
    assert not ruta_db.exists()


def test_abrir_archivo_sin_tablas_se_trata_como_no_inicializada(ruta_db):
    ruta_db.touch()
    with pytest.raises(ErrorBaseNoInicializada):
        abrir_base(ruta_db)


def test_abrir_archivo_que_no_es_sqlite_se_trata_como_no_inicializada(ruta_db):
    ruta_db.write_text("esto no es una base de datos", encoding="utf-8")
    with pytest.raises(ErrorBaseNoInicializada):
        abrir_base(ruta_db)


def test_ruta_base_usa_la_variable_de_entorno(monkeypatch, tmp_path):
    monkeypatch.setenv("RESERVAS_DB", str(tmp_path / "otra.db"))
    assert ruta_base() == tmp_path / "otra.db"


def test_ruta_base_por_defecto_es_datos_reservas_db(monkeypatch):
    monkeypatch.delenv("RESERVAS_DB", raising=False)
    assert ruta_base() == RUTA_BASE_POR_DEFECTO
    assert RUTA_BASE_POR_DEFECTO.parts[-2:] == ("datos", "reservas.db")


# --- Persistencia al cerrar y reabrir (RF-07, CA-10) ---

def test_reserva_activa_y_cancelada_persisten_al_cerrar_y_reabrir(ruta_db):
    ahora = datetime(2030, 11, 1, 9, 0)
    crear_base(ruta_db)
    conexion = abrir_base(ruta_db)
    crear_reserva(conexion, "MIC-01", "Ana Prueba",
                  "2030-11-03 10:00", "2030-11-03 11:00", ahora=ahora)
    crear_reserva(conexion, "MIC-02", "Beto Prueba",
                  "2030-11-03 10:00", "2030-11-03 11:00", ahora=ahora)
    cancelar_reserva(conexion, "R-0002", ahora=datetime(2030, 11, 2, 8, 30))
    conexion.close()

    reabierta = abrir_base(ruta_db)
    try:
        activa = obtener_reserva(reabierta, 1)
        assert activa["unidad_id"] == "MIC-01"
        assert activa["solicitante"] == "Ana Prueba"
        assert activa["inicio"] == "2030-11-03 10:00"
        assert activa["fin"] == "2030-11-03 11:00"
        assert activa["estado"] == "activa"
        assert activa["creada_en"] == "2030-11-01 09:00:00"
        assert activa["cancelada_en"] is None

        cancelada = obtener_reserva(reabierta, 2)
        assert cancelada["unidad_id"] == "MIC-02"
        assert cancelada["solicitante"] == "Beto Prueba"
        assert cancelada["estado"] == "cancelada"
        assert cancelada["cancelada_en"] == "2030-11-02 08:30:00"

        # Tras reabrir, la activa sigue bloqueando y la cancelada no.
        assert not consultar_disponibilidad(
            reabierta, "MIC-01", "2030-11-03 10:00", "2030-11-03 11:00", ahora=ahora
        ).reservable
        assert consultar_disponibilidad(
            reabierta, "MIC-02", "2030-11-03 10:00", "2030-11-03 11:00", ahora=ahora
        ).reservable

        # Los IDs no se reutilizan tras reabrir (S-07).
        nueva = crear_reserva(reabierta, "MIC-02", "Caro Prueba",
                              "2030-11-03 10:00", "2030-11-03 11:00", ahora=ahora)
        assert formatear_id_reserva(nueva) == "R-0003"
    finally:
        reabierta.close()
