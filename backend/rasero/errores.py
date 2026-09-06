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


class ConteoInvalido(ErrorDominio):
    codigo = "conteo_invalido"
    status_code = 409


class TraspasoInvalido(ErrorDominio):
    codigo = "traspaso_invalido"
    status_code = 409


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


# --------------------------------------------------------------------------
# 005-promociones-inteligentes
# --------------------------------------------------------------------------


class RangoFechasInvalido(ErrorDominio):
    codigo = "rango_fechas_invalido"
    status_code = 400

    _POR_DEFECTO = "El rango de fechas no es válido: revisa que 'hasta' no sea anterior a 'desde'."

    def __init__(self, mensaje: str = _POR_DEFECTO):
        super().__init__(mensaje)


class RedencionInvalida(ErrorDominio):
    codigo = "redencion_invalida"
    status_code = 400


class RedencionDeGrupoControl(ErrorDominio):
    codigo = "redencion_de_grupo_control"
    status_code = 400

    def __init__(self):
        super().__init__(
            "Este cliente está en el grupo de control del experimento y no tiene derecho al "
            "descuento de reactivación."
        )


class CuponFueraDeVentana(ErrorDominio):
    codigo = "cupon_fuera_de_ventana"
    status_code = 400

    def __init__(self):
        super().__init__("El cupón no está vigente en la fecha de esta venta.")


class ParametrosExperimentoInvalidos(ErrorDominio):
    codigo = "parametros_experimento_invalidos"
    status_code = 400


class ExperimentoEnCurso(ErrorDominio):
    codigo = "experimento_en_curso"
    status_code = 409

    def __init__(self):
        super().__init__(
            "Ya hay un experimento de reactivación en curso. Ciérralo antes de crear otro."
        )


class CierreExperimentoNoAplicable(ErrorDominio):
    codigo = "cierre_experimento_no_aplicable"
    status_code = 409


# --------------------------------------------------------------------------
# 006-caja-mermas-fraude
# --------------------------------------------------------------------------


class ErrorCaja(ErrorDominio):
    """Error de dominio de 006. Lleva su propio `codigo` y `status_code` por instancia —
    los prefijos `caja_` mantienen los códigos del contrato agrupados y legibles.
    """

    def __init__(self, codigo: str, mensaje: str, *, status_code: int = 400):
        self.codigo = codigo
        self.status_code = status_code
        super().__init__(mensaje)


# 001 User Story 5 (`conteo_fisico`/`conteo_renglon`) ya está implementada; la excepción
# `CajaBloqueadoPor001` que devolvía `409 caja_bloqueado_por_001` se retiró al desbloquear
# `POST /caja/cruce-operador` y la rama de conteo de `POST /caja/mermas`.


# --------------------------------------------------------------------------
# 007-pagos-seguridad
# --------------------------------------------------------------------------


class ErrorPagos(ErrorDominio):
    """Error de dominio de 007. Lleva su propio `codigo` y `status_code` por instancia — los
    prefijos `pagos_` mantienen los códigos del contrato agrupados y legibles.
    """

    def __init__(self, codigo: str, mensaje: str, *, status_code: int = 400):
        self.codigo = codigo
        self.status_code = status_code
        super().__init__(mensaje)


class PanDetectado(ErrorPagos):
    """Se recibió un número de tarjeta completo donde no correspondía. Se rechaza y se registra en
    la bitácora SIN el número (FR-018, SC-008). El PAN nunca se almacena, registra ni transmite.
    """

    def __init__(self):
        super().__init__(
            "pagos_pan_detectado",
            "El sistema no puede guardar un número de tarjeta completo. Sólo se conservan la marca "
            "y los últimos cuatro dígitos. Revisa la integración del datáfono.",
        )
