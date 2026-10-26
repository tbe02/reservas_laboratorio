"""Excepciones del sistema. Sus mensajes están pensados para mostrarse al usuario."""


class ErrorReservas(Exception):
    """Base de todos los errores esperables del sistema."""


class ErrorValidacion(ErrorReservas):
    """Los datos ingresados no cumplen una regla de negocio."""


class ErrorSuperposicion(ErrorReservas):
    """El intervalo choca con reservas activas de la misma unidad (RN-07)."""

    def __init__(self, mensaje, conflictos):
        super().__init__(mensaje)
        self.conflictos = conflictos


class ErrorBaseNoInicializada(ErrorReservas):
    """La base no existe o no tiene las tablas (S-09, S-17)."""

    def __init__(self):
        super().__init__(
            "La base de datos no está inicializada. "
            "Ejecutá: python -m reservas inicializar"
        )
