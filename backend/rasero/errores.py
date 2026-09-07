"""Excepciones de dominio. Cada una lleva un mensaje orientado a la acción correctiva del
operador — nunca una traza técnica (Principio IV, prohibición explícita en el contrato).
"""

from decimal import Decimal


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


# --------------------------------------------------------------------------
# Identidad de sesión de turno (Principio VI, enmienda v2.4.0; User Story 11)
# --------------------------------------------------------------------------

_MENSAJE_SESION = "Tu turno expiró o fue cerrado. Abre turno de nuevo."


class SesionInvalida(ErrorDominio):
    """El token de sesión de turno falta, tiene firma inválida o malformada, refiere un turno ya
    cerrado, o refiere un operador desactivado. Códigos nuevos, sin colisión con los existentes.
    """

    codigo = "sesion_invalida"
    status_code = 401

    def __init__(self, mensaje: str = _MENSAJE_SESION):
        super().__init__(mensaje)


class SesionExpirada(ErrorDominio):
    """El token de sesión de turno superó su `exp` (12 h desde la emisión)."""

    codigo = "sesion_expirada"
    status_code = 401

    def __init__(self, mensaje: str = _MENSAJE_SESION):
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


class ValorInvalido(ErrorDominio):
    codigo = "valor_invalido"
    status_code = 422


class ExistenciaInsuficiente(ErrorDominio):
    """Una venta o un traspaso pidió más de lo que hay en existencia disponible. Bloqueo duro,
    sin excepción ni autorización de encargado (spec 001, Corrección 2026-09-07): vender o
    traspasar algo que no está en inventario no tiene sentido de negocio. 409 (conflicto de
    estado real), no 422 (no es un error de forma). Sin colisión de código: el resto de los 409
    del sistema usan códigos propios (`conteo_invalido`, `traspaso_invalido`, `venta_ya_*`, …).
    """

    codigo = "existencia_insuficiente"
    status_code = 409

    def __init__(self, nombre_producto: str, disponible: Decimal, solicitado: Decimal):
        super().__init__(
            f"No hay suficiente existencia de {nombre_producto}: disponible "
            f"{disponible}, solicitado {solicitado}. Ajusta la cantidad o "
            "haz un conteo físico si crees que el dato está desactualizado."
        )


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


class IdentificadorInvalido(ErrorDominio):
    codigo = "identificador_invalido"
    status_code = 422

    def __init__(self):
        super().__init__(
            "Identificador inválido: debe ser una cédula (10 dígitos) o RUC de persona natural "
            "(13 dígitos) válidos."
        )


class IdentificadorDuplicado(ErrorDominio):
    codigo = "identificador_duplicado"
    status_code = 409

    def __init__(self):
        super().__init__(
            "Ya hay otro cliente registrado con esa cédula o RUC. Búscalo en vez de crear uno "
            "nuevo; el sistema nunca fusiona clientes automáticamente."
        )


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


class ErrorAdministracion(ErrorDominio):
    """Error de dominio de la administración de datos maestros (sucursal, producto, categoria,
    zona de exhibición, medio de pago). Lleva su propio `codigo` y `status_code` por instancia;
    los prefijos `admin_` mantienen los códigos del contrato agrupados y legibles — mismo patrón
    que `ErrorCaja` (006) y `ErrorPagos` (007).
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
