"""Reglas de negocio: validaciones y creación de reservas.

Las fechas se manejan como `datetime` sin zona, interpretadas siempre en
hora de Buenos Aires (S-01). En la base se guardan como texto con formato
fijo, que se ordena y compara igual que las fechas (D-06).
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from reservas import persistencia
from reservas.errores import ErrorValidacion

ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")
FORMATO_FECHA = "%Y-%m-%d %H:%M"
FORMATO_REGISTRO = "%Y-%m-%d %H:%M:%S"
# strptime acepta "2030-1-3 9:00"; el formato exige ceros a la izquierda.
PATRON_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}")


def ahora_buenos_aires():
    """Hora actual de Buenos Aires, sin zona."""
    return datetime.now(ZONA_HORARIA).replace(tzinfo=None)


def _normalizar_ahora(ahora):
    if ahora is None:
        return ahora_buenos_aires()
    if ahora.tzinfo is not None:
        return ahora.astimezone(ZONA_HORARIA).replace(tzinfo=None)
    return ahora


def formatear_id_reserva(reserva_id):
    return f"R-{reserva_id:04d}"


def normalizar_unidad(unidad):
    return unidad.upper()


def validar_solicitante(solicitante):
    """RN-02: devuelve el solicitante sin espacios en los extremos (S-06)."""
    solicitante = solicitante.strip()
    if not solicitante:
        raise ErrorValidacion("El solicitante no puede estar vacío.")
    return solicitante


def parsear_fecha(texto, campo):
    """RN-03: convierte 'AAAA-MM-DD HH:MM' en datetime."""
    if not PATRON_FECHA.fullmatch(texto):
        raise ErrorValidacion(
            f"La fecha de {campo} '{texto}' no respeta el formato "
            "AAAA-MM-DD HH:MM (ej. 2030-11-03 10:00)."
        )
    try:
        return datetime.strptime(texto, FORMATO_FECHA)
    except ValueError:
        raise ErrorValidacion(
            f"La fecha de {campo} '{texto}' no es una fecha válida."
        ) from None


def _validar_unidad_e_intervalo(conexion, unidad, inicio, fin):
    """RN-01, RN-03 y RN-04. Devuelve (unidad_id, inicio, fin) normalizados."""
    unidad_id = normalizar_unidad(unidad)
    if not persistencia.existe_unidad(conexion, unidad_id):
        raise ErrorValidacion(f"La unidad '{unidad}' no existe en el inventario.")
    inicio_dt = parsear_fecha(inicio, "inicio")
    fin_dt = parsear_fecha(fin, "fin")
    if inicio_dt >= fin_dt:
        raise ErrorValidacion("El inicio debe ser anterior al fin.")
    return unidad_id, inicio_dt, fin_dt


def crear_reserva(conexion, unidad, solicitante, inicio, fin, ahora=None):
    """Crea una reserva activa y devuelve su ID numérico.

    Lanza ErrorValidacion si no se cumple alguna regla (RN-01 a RN-05).
    """
    ahora = _normalizar_ahora(ahora)
    unidad_id, inicio_dt, fin_dt = _validar_unidad_e_intervalo(
        conexion, unidad, inicio, fin
    )
    solicitante = validar_solicitante(solicitante)
    if inicio_dt <= ahora:
        raise ErrorValidacion(
            "No se puede reservar: el inicio debe ser posterior al momento actual."
        )
    return persistencia.insertar_reserva(
        conexion,
        unidad_id,
        solicitante,
        inicio_dt.strftime(FORMATO_FECHA),
        fin_dt.strftime(FORMATO_FECHA),
        ahora.strftime(FORMATO_REGISTRO),
    )
