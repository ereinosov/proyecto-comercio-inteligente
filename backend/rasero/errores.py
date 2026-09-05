"""Excepciones de dominio. Cada una lleva un mensaje orientado a la acción correctiva del
operador — nunca una traza técnica (Principio IV, prohibición explícita en el contrato).
"""


class ErrorDominio(Exception):
    codigo: str = "error"
    status_code: int = 400

    def __init__(self, mensaje: str):
        self.mensaje = mensaje
        super().__init__(mensaje)


class PinIncorrecto(ErrorDominio):
    codigo = "pin_incorrecto"
    status_code = 401

    def __init__(self):
        super().__init__("PIN incorrecto. Verifica los 4 dígitos o pide a un encargado que lo reasigne.")


class OperadorInvalido(ErrorDominio):
    codigo = "operador_invalido"
    status_code = 422

    def __init__(self):
        super().__init__("El operador no existe o está inactivo. Elige otro de la lista.")


class TurnoInvalido(ErrorDominio):
    codigo = "turno_invalido"
    status_code = 422

    def __init__(self, mensaje: str = "El turno indicado no existe."):
        super().__init__(mensaje)


class RenglonInvalido(ErrorDominio):
    codigo = "renglon_invalido"
    status_code = 422


class AnulacionNoAutorizada(ErrorDominio):
    codigo = "anulacion_no_autorizada"
    status_code = 403

    def __init__(self):
        super().__init__(
            "Solo un encargado puede anular una venta de un turno ya cerrado."
        )


class VentaYaAnulada(ErrorDominio):
    codigo = "venta_ya_anulada"
    status_code = 409

    def __init__(self):
        super().__init__("Esta venta ya estaba anulada.")


class RecursoNoEncontrado(ErrorDominio):
    codigo = "no_encontrado"
    status_code = 404


class VentaYaVinculada(ErrorDominio):
    codigo = "venta_ya_vinculada"
    status_code = 409

    def __init__(self):
        super().__init__("Esta venta ya está vinculada a otro cliente.")


class SugerenciaYaAplicada(ErrorDominio):
    codigo = "sugerencia_ya_aplicada"
    status_code = 409

    def __init__(self):
        super().__init__("Esta sugerencia ya había sido aplicada.")


class SerieSinteticaInvalida(ErrorDominio):
    codigo = "serie_sintetica_invalida"
    status_code = 400


class RelacionSustitucionInvalida(ErrorDominio):
    codigo = "relacion_sustitucion_invalida"
    status_code = 400


class RelacionSustitucionDuplicada(ErrorDominio):
    codigo = "relacion_sustitucion_duplicada"
    status_code = 409

    def __init__(self):
        super().__init__("Esa relación de sustitución (en esa dirección) ya estaba declarada.")
