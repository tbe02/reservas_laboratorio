import pytest

from reservas.persistencia import abrir_base, crear_base


@pytest.fixture
def ruta_db(tmp_path):
    """Ruta de una base temporal, todavía sin crear."""
    return tmp_path / "reservas.db"


@pytest.fixture
def conexion(ruta_db):
    """Conexión a una base temporal inicializada con el inventario."""
    crear_base(ruta_db)
    conexion = abrir_base(ruta_db)
    yield conexion
    conexion.close()
