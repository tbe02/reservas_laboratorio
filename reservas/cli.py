"""Interfaz de línea de comandos: `python -m reservas <comando>`.

Solo interpreta argumentos, pide confirmaciones y muestra resultados. Las
reglas de negocio están en `reservas.reglas` y el acceso a datos en
`reservas.persistencia`.

Códigos de salida (S-10): 0 si la operación se completa; 1 si hay un error
o el usuario no confirma.
"""

import argparse
import sqlite3
import sys

from reservas import persistencia, reglas
from reservas.errores import ErrorReservas

EXITO = 0
FALLO = 1

RESPUESTAS_AFIRMATIVAS = {"s", "si", "sí"}
ENCABEZADOS_RESERVA = ("ID", "Unidad", "Solicitante", "Inicio", "Fin", "Estado")

# argparse escribe sus errores en inglés; se traducen los más comunes.
TRADUCCIONES_ARGPARSE = [
    ("the following arguments are required", "faltan argumentos obligatorios"),
    ("unrecognized arguments", "argumentos no reconocidos"),
    ("invalid choice", "opción inválida"),
    ("choose from", "opciones válidas"),
    ("expected one argument", "se esperaba un valor"),
    ("argument ", "argumento "),
]


# --- argparse en español ---

class _Formateador(argparse.HelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = "uso: "
        return super().add_usage(usage, actions, groups, prefix)


class _Analizador(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", _Formateador)
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "argumentos"
        self._optionals.title = "opciones"
        self.add_argument(
            "-h", "--help", action="help", help="muestra esta ayuda y termina"
        )

    def error(self, message):
        # argparse sale con 2; la especificación pide 1 para cualquier error.
        for original, traduccion in TRADUCCIONES_ARGPARSE:
            message = message.replace(original, traduccion)
        self.print_usage(sys.stderr)
        print(f"Error: {message}", file=sys.stderr)
        raise SystemExit(FALLO)


def crear_analizador():
    analizador = _Analizador(
        prog="python -m reservas",
        description="Reservas de equipos de laboratorio.",
    )
    comandos = analizador.add_subparsers(
        dest="comando", required=True, title="comandos", metavar="COMANDO"
    )

    comandos.add_parser(
        "inicializar", help="crea la base y carga el inventario (borra las reservas)"
    )
    comandos.add_parser("unidades", help="muestra las unidades del inventario")

    disponibilidad = comandos.add_parser(
        "disponibilidad", help="indica si una unidad está libre en un intervalo"
    )
    disponibilidad.add_argument("unidad", metavar="UNIDAD")
    disponibilidad.add_argument("--desde", required=True, metavar="FECHA",
                                help="inicio, 'AAAA-MM-DD HH:MM'")
    disponibilidad.add_argument("--hasta", required=True, metavar="FECHA",
                                help="fin, 'AAAA-MM-DD HH:MM'")

    reservar = comandos.add_parser("reservar", help="crea una reserva")
    reservar.add_argument("unidad", metavar="UNIDAD")
    reservar.add_argument("--solicitante", required=True, metavar="NOMBRE")
    reservar.add_argument("--inicio", required=True, metavar="FECHA",
                          help="'AAAA-MM-DD HH:MM'")
    reservar.add_argument("--fin", required=True, metavar="FECHA",
                          help="'AAAA-MM-DD HH:MM'")

    cancelar = comandos.add_parser("cancelar", help="cancela una reserva")
    cancelar.add_argument("id", metavar="ID", help="ej. R-0001")

    listar = comandos.add_parser("listar", help="muestra las reservas guardadas")
    listar.add_argument("--unidad", metavar="UNIDAD")
    listar.add_argument("--estado", choices=reglas.ESTADOS)

    return analizador


# --- Salida ---

def _imprimir_tabla(encabezados, filas):
    anchos = [max(len(str(valor)) for valor in columna)
              for columna in zip(encabezados, *filas)]
    for fila in (encabezados, *filas):
        print("  ".join(str(v).ljust(a) for v, a in zip(fila, anchos)).rstrip())


def _fila_reserva(reserva):
    return (
        reglas.formatear_id_reserva(reserva["id"]),
        reserva["unidad_id"],
        reserva["solicitante"],
        reserva["inicio"],
        reserva["fin"],
        reserva["estado"],
    )


def _confirmar(pregunta, leer_respuesta):
    """S-08: solo 's', 'si' o 'sí' confirman; cualquier otra cosa es no."""
    try:
        respuesta = leer_respuesta(f"{pregunta} (s/n): ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return respuesta.strip().lower() in RESPUESTAS_AFIRMATIVAS


def _plural_reservas(cantidad):
    return "1 reserva" if cantidad == 1 else f"{cantidad} reservas"


# --- Comandos ---

def _inicializar(args, ahora, leer_respuesta):
    ruta = persistencia.ruta_base()
    cantidad = persistencia.contar_reservas_en(ruta)
    if cantidad > 0:
        print(f"La base tiene {_plural_reservas(cantidad)}. "
              "Si continuás, se borrarán todas.")
        if not _confirmar("¿Reiniciar la base?", leer_respuesta):
            print("Operación cancelada. No se modificó la base.")
            return FALLO
    persistencia.crear_base(ruta)
    print(f"Base de datos creada en {ruta} con las unidades del inventario.")
    return EXITO


def _unidades(conexion, args, ahora, leer_respuesta):
    filas = [(u["id"], u["equipo"]) for u in persistencia.listar_unidades(conexion)]
    _imprimir_tabla(("ID", "Equipo"), filas)
    return EXITO


def _disponibilidad(conexion, args, ahora, leer_respuesta):
    resultado = reglas.consultar_disponibilidad(
        conexion, args.unidad, args.desde, args.hasta, ahora=ahora
    )
    intervalo = f"del {args.desde} al {args.hasta}"
    if resultado.reservable:
        print(f"La unidad {resultado.unidad_id} está libre {intervalo}.")
    # D-24 / S-18: si está en el pasado y ocupado, se informan las dos cosas.
    if resultado.en_pasado:
        print(f"El intervalo {intervalo} no es reservable: el inicio ya pasó.")
    if not resultado.libre:
        print(f"La unidad {resultado.unidad_id} está ocupada {intervalo}. "
              "Reservas que la bloquean:")
        _imprimir_tabla(ENCABEZADOS_RESERVA,
                        [_fila_reserva(r) for r in resultado.conflictos])
    return EXITO


def _reservar(conexion, args, ahora, leer_respuesta):
    reserva_id = reglas.crear_reserva(
        conexion, args.unidad, args.solicitante, args.inicio, args.fin, ahora=ahora
    )
    reserva = persistencia.obtener_reserva(conexion, reserva_id)
    print(f"Reserva creada: {reglas.formatear_id_reserva(reserva_id)} "
          f"({reserva['unidad_id']}, {reserva['inicio']} a {reserva['fin']}, "
          f"{reserva['solicitante']}).")
    return EXITO


def _cancelar(conexion, args, ahora, leer_respuesta):
    # Se valida antes de preguntar, para no pedir confirmación en vano;
    # cancelar_reserva vuelve a validar dentro de la transacción.
    reserva = reglas.obtener_reserva_cancelable(conexion, args.id, ahora=ahora)
    reserva_id = reglas.formatear_id_reserva(reserva["id"])
    _imprimir_tabla(ENCABEZADOS_RESERVA, [_fila_reserva(reserva)])
    if not _confirmar(f"¿Cancelar la reserva {reserva_id}?", leer_respuesta):
        print("Operación cancelada. No se modificó la reserva.")
        return FALLO
    reglas.cancelar_reserva(conexion, args.id, ahora=ahora)
    print(f"Reserva {reserva_id} cancelada.")
    return EXITO


def _listar(conexion, args, ahora, leer_respuesta):
    reservas = reglas.listar_reservas(conexion, unidad=args.unidad, estado=args.estado)
    if not reservas:
        print("No hay reservas.")
        return EXITO
    _imprimir_tabla(ENCABEZADOS_RESERVA, [_fila_reserva(r) for r in reservas])
    return EXITO


COMANDOS_CON_BASE = {
    "unidades": _unidades,
    "disponibilidad": _disponibilidad,
    "reservar": _reservar,
    "cancelar": _cancelar,
    "listar": _listar,
}


def _ejecutar(args, ahora, leer_respuesta):
    if args.comando == "inicializar":
        return _inicializar(args, ahora, leer_respuesta)
    conexion = persistencia.abrir_base(persistencia.ruta_base())
    try:
        return COMANDOS_CON_BASE[args.comando](conexion, args, ahora, leer_respuesta)
    finally:
        conexion.close()


def main(argv=None, ahora=None, leer_respuesta=input):
    """Punto de entrada. Devuelve el código de salida.

    `ahora` y `leer_respuesta` existen solo para las pruebas: la CLI real
    siempre usa la hora actual y la entrada estándar (D-08).
    """
    try:
        args = crear_analizador().parse_args(argv)
    except SystemExit as salida:
        return salida.code if isinstance(salida.code, int) else FALLO
    try:
        return _ejecutar(args, ahora, leer_respuesta)
    except ErrorReservas as error:
        print(f"Error: {error}", file=sys.stderr)
    except sqlite3.Error as error:
        print(f"Error: no se pudo acceder a la base de datos ({error}).",
              file=sys.stderr)
    except OSError as error:
        print(f"Error: no se pudo acceder al archivo ({error.strerror}).",
              file=sys.stderr)
    return FALLO
