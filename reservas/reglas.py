"""Reglas de negocio: validaciones, disponibilidad, creación y cancelación.

Las fechas se manejan como `datetime` sin zona, interpretadas siempre en
hora de Buenos Aires (S-01). En la base se guardan como texto con formato
fijo, que se ordena y compara igual que las fechas (D-06).
"""

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from reservas import persistencia
from reservas.errores import (
    ErrorReservaNoEncontrada,
    ErrorReservaYaCancelada,
    ErrorSuperposicion,
    ErrorValidacion,
)

ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")
FORMATO_FECHA = "%Y-%m-%d %H:%M"
FORMATO_REGISTRO = "%Y-%m-%d %H:%M:%S"
# strptime acepta "2030-1-3 9:00"; el formato exige ceros a la izquierda.
PATRON_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}")
PATRON_ID_RESERVA = re.compile(r"R-([0-9]+)", re.IGNORECASE)


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


def parsear_id_reserva(texto):
    """Convierte 'R-0001' (sin distinguir mayúsculas, S-06) en 1.

    Lanza ErrorReservaNoEncontrada si el texto no tiene forma de ID.
    """
    coincidencia = PATRON_ID_RESERVA.fullmatch(texto)
    if not coincidencia:
        raise ErrorReservaNoEncontrada(
            f"'{texto}' no es un ID de reserva válido (ej. R-0001)."
        )
    return int(coincidencia.group(1))


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


def _validar_unidad(conexion, unidad):
    """RN-01: devuelve el ID de unidad normalizado (S-06)."""
    unidad_id = normalizar_unidad(unidad)
    if not persistencia.existe_unidad(conexion, unidad_id):
        raise ErrorValidacion(f"La unidad '{unidad}' no existe en el inventario.")
    return unidad_id


def _validar_unidad_e_intervalo(conexion, unidad, inicio, fin):
    """RN-01, RN-03 y RN-04. Devuelve (unidad_id, inicio, fin) normalizados."""
    unidad_id = _validar_unidad(conexion, unidad)
    inicio_dt = parsear_fecha(inicio, "inicio")
    fin_dt = parsear_fecha(fin, "fin")
    if inicio_dt >= fin_dt:
        raise ErrorValidacion("El inicio debe ser anterior al fin.")
    return unidad_id, inicio_dt, fin_dt


@dataclass(frozen=True)
class Disponibilidad:
    """Resultado de evaluar un intervalo de una unidad."""

    unidad_id: str
    inicio: datetime
    fin: datetime
    en_pasado: bool
    conflictos: list

    @property
    def libre(self):
        return not self.conflictos

    @property
    def reservable(self):
        return self.libre and not self.en_pasado


def consultar_disponibilidad(conexion, unidad, inicio, fin, ahora=None):
    """Evalúa si el intervalo [inicio, fin) de la unidad se puede reservar.

    Es la función compartida con crear_reserva (RN-10): aplica RN-01 y RN-03
    a RN-07. Lanza ErrorValidacion si los datos son inválidos; si el intervalo
    está ocupado o en el pasado, lo informa en el resultado (S-03, S-15).
    """
    ahora = _normalizar_ahora(ahora)
    unidad_id, inicio_dt, fin_dt = _validar_unidad_e_intervalo(
        conexion, unidad, inicio, fin
    )
    conflictos = persistencia.buscar_conflictos(
        conexion,
        unidad_id,
        inicio_dt.strftime(FORMATO_FECHA),
        fin_dt.strftime(FORMATO_FECHA),
    )
    return Disponibilidad(
        unidad_id=unidad_id,
        inicio=inicio_dt,
        fin=fin_dt,
        en_pasado=inicio_dt <= ahora,
        conflictos=conflictos,
    )


def _mensaje_superposicion(unidad_id, conflictos):
    detalle = ", ".join(
        f"{formatear_id_reserva(c['id'])} ({c['inicio']} a {c['fin']})"
        for c in conflictos
    )
    return f"La unidad {unidad_id} ya está reservada en ese horario: {detalle}."


def crear_reserva(conexion, unidad, solicitante, inicio, fin, ahora=None):
    """Crea una reserva activa y devuelve su ID numérico.

    Lanza ErrorValidacion si no se cumple alguna regla (RN-01 a RN-05) y
    ErrorSuperposicion si choca con otra reserva activa (RN-07). La
    verificación y la inserción ocurren en la misma transacción (D-13).
    """
    ahora = _normalizar_ahora(ahora)
    with persistencia.transaccion_inmediata(conexion):
        disponibilidad = consultar_disponibilidad(
            conexion, unidad, inicio, fin, ahora=ahora
        )
        solicitante = validar_solicitante(solicitante)
        if disponibilidad.en_pasado:
            raise ErrorValidacion(
                "No se puede reservar: el inicio debe ser posterior al momento actual."
            )
        if not disponibilidad.libre:
            raise ErrorSuperposicion(
                _mensaje_superposicion(
                    disponibilidad.unidad_id, disponibilidad.conflictos
                ),
                disponibilidad.conflictos,
            )
        return persistencia.insertar_reserva(
            conexion,
            disponibilidad.unidad_id,
            solicitante,
            disponibilidad.inicio.strftime(FORMATO_FECHA),
            disponibilidad.fin.strftime(FORMATO_FECHA),
            ahora.strftime(FORMATO_REGISTRO),
        )


def buscar_reserva(conexion, reserva_id_texto):
    """Devuelve la reserva con ese ID ('R-0001'); lanza ErrorReservaNoEncontrada."""
    reserva_id = parsear_id_reserva(reserva_id_texto)
    reserva = persistencia.obtener_reserva(conexion, reserva_id)
    if reserva is None:
        raise ErrorReservaNoEncontrada(
            f"No existe la reserva {formatear_id_reserva(reserva_id)}."
        )
    return reserva


def obtener_reserva_cancelable(conexion, reserva_id_texto, ahora=None):
    """Devuelve la reserva si se puede cancelar; si no, lanza el error.

    Errores: no existe, ya estaba cancelada (RN-12) o ya empezó (S-19).
    """
    ahora = _normalizar_ahora(ahora)
    reserva = buscar_reserva(conexion, reserva_id_texto)
    reserva_id = formatear_id_reserva(reserva["id"])
    if reserva["estado"] == "cancelada":
        raise ErrorReservaYaCancelada(
            f"La reserva {reserva_id} ya está "
            f"cancelada (desde {reserva['cancelada_en']})."
        )
    if datetime.strptime(reserva["inicio"], FORMATO_FECHA) <= ahora:
        raise ErrorValidacion(
            f"No se puede cancelar la reserva {reserva_id}: ya empezó "
            f"(inicio {reserva['inicio']})."
        )
    return reserva


def cancelar_reserva(conexion, reserva_id_texto, ahora=None):
    """Cancela una reserva activa y devuelve la reserva actualizada.

    No borra el registro: cambia el estado a 'cancelada' y guarda
    cancelada_en (RN-11). Si la reserva no se puede cancelar, lanza el error
    de obtener_reserva_cancelable y no modifica nada.
    """
    ahora = _normalizar_ahora(ahora)
    with persistencia.transaccion_inmediata(conexion):
        reserva = obtener_reserva_cancelable(conexion, reserva_id_texto, ahora=ahora)
        persistencia.marcar_cancelada(
            conexion, reserva["id"], ahora.strftime(FORMATO_REGISTRO)
        )
        return persistencia.obtener_reserva(conexion, reserva["id"])


ESTADOS = ("activa", "cancelada")


def listar_reservas(conexion, unidad=None, estado=None):
    """Reservas guardadas, ordenadas por inicio y luego por ID (S-16).

    Filtros opcionales: unidad (debe existir, RN-01) y estado.
    """
    unidad_id = _validar_unidad(conexion, unidad) if unidad is not None else None
    if estado is not None and estado not in ESTADOS:
        raise ErrorValidacion(
            f"El estado '{estado}' no es válido (activa o cancelada)."
        )
    return persistencia.listar_reservas(conexion, unidad_id, estado)
