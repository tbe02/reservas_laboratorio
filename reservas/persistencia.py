"""Capa de persistencia: archivo SQLite, esquema e inventario.

No contiene reglas de negocio. Nunca se ejecuta DELETE sobre `reservas`:
reiniciar la base borra el archivo completo (S-13).
"""

import csv
import os
import sqlite3
from pathlib import Path

from reservas.errores import ErrorBaseNoInicializada

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_BASE_POR_DEFECTO = RAIZ_PROYECTO / "datos" / "reservas.db"
RUTA_INVENTARIO = RAIZ_PROYECTO / "datos" / "inventario.csv"

ESQUEMA = """
CREATE TABLE unidades (
    id      TEXT PRIMARY KEY,
    equipo  TEXT NOT NULL
);

CREATE TABLE reservas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    unidad_id     TEXT NOT NULL REFERENCES unidades(id),
    solicitante   TEXT NOT NULL CHECK (length(trim(solicitante)) > 0),
    inicio        TEXT NOT NULL,
    fin           TEXT NOT NULL,
    estado        TEXT NOT NULL DEFAULT 'activa'
                  CHECK (estado IN ('activa', 'cancelada')),
    creada_en     TEXT NOT NULL,
    cancelada_en  TEXT,
    CHECK (inicio < fin)
);

CREATE INDEX idx_reservas_unidad_estado ON reservas (unidad_id, estado);
"""

TABLAS_REQUERIDAS = {"unidades", "reservas"}


def ruta_base():
    """Ruta del archivo de la base: `RESERVAS_DB` o `datos/reservas.db`."""
    ruta = os.environ.get("RESERVAS_DB")
    return Path(ruta) if ruta else RUTA_BASE_POR_DEFECTO


def leer_inventario(ruta_csv=RUTA_INVENTARIO):
    """Devuelve el inventario como lista de tuplas (id, equipo)."""
    with open(ruta_csv, newline="", encoding="utf-8") as archivo:
        return [(fila["id"], fila["equipo"]) for fila in csv.DictReader(archivo)]


def _conectar(ruta, crear):
    # mode=rw evita que sqlite3 cree un archivo vacío si la base no existe.
    modo = "rwc" if crear else "rw"
    conexion = sqlite3.connect(
        f"{Path(ruta).resolve().as_uri()}?mode={modo}",
        uri=True,
        isolation_level=None,
    )
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_base(ruta, inventario=None):
    """Crea la base desde cero con el esquema y el inventario.

    Si el archivo ya existe, lo borra antes (S-13): los IDs de reserva
    vuelven a empezar en R-0001.
    """
    if inventario is None:
        inventario = leer_inventario()
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.unlink(missing_ok=True)

    conexion = _conectar(ruta, crear=True)
    try:
        conexion.executescript(ESQUEMA)
        with conexion:
            conexion.execute("BEGIN")
            conexion.executemany(
                "INSERT INTO unidades (id, equipo) VALUES (?, ?)", inventario
            )
    finally:
        conexion.close()


def abrir_base(ruta):
    """Abre una base existente e inicializada.

    Lanza ErrorBaseNoInicializada si el archivo no existe o no tiene las
    tablas (S-09, S-17).
    """
    if not Path(ruta).is_file():
        raise ErrorBaseNoInicializada()
    conexion = _conectar(ruta, crear=False)
    try:
        tablas = {
            fila["name"]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    except sqlite3.DatabaseError:
        # El archivo existe pero no es una base SQLite válida.
        conexion.close()
        raise ErrorBaseNoInicializada() from None
    if not TABLAS_REQUERIDAS <= tablas:
        conexion.close()
        raise ErrorBaseNoInicializada()
    return conexion


def listar_unidades(conexion):
    """Unidades del inventario, en el orden en que se cargaron."""
    return conexion.execute(
        "SELECT id, equipo FROM unidades ORDER BY rowid"
    ).fetchall()
