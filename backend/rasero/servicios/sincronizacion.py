"""Reconciliación de operaciones ejecutadas sin conectividad
(001-core-ventas-inventario, US8 — T085).

El servidor recibe un lote de operaciones registradas offline, lo **ordena por
`marca_tiempo_origen` ascendente** (FR-038) y lo aplica en ese orden. Ante dos operaciones sobre
el mismo `recurso_afectado` prevalece la de marca más antigua, **en las dos direcciones**
(FR-039, research.md #6):

- si la que llega es más nueva (o igual) que una ya sincronizada del mismo recurso, la que llega
  queda `conflicto_resuelto` con `id_operacion_prevaleciente` apuntando a la que ganó, y **no se
  aplica**;
- si la que llega es más antigua que una ya sincronizada, se aplica ella y la ya sincronizada
  pasa a `conflicto_resuelto` apuntando a la que llega.

La operación desplazada **permanece visible** (FR-040): su fila queda en `conflicto_resuelto`,
nunca se elimina ni se oculta. Se conserva `instante_recepcion` junto a `marca_tiempo_origen`
(FR-041) para que un reloj de dispositivo desviado sea detectable.

*Alcance del efecto* (research.md #6, decisión registrada): la resolución de conflictos y la
trazabilidad son completas. El efecto de negocio de una operación *ganadora* se materializa
despachando su `carga` al servicio correspondiente; el de una operación *desplazada que ya se
había aplicado* NO se revierte —deshacer un movimiento de inventario o de dinero exige su propio
movimiento compensatorio, fuera del alcance de este módulo—: lo que exige FR-040 es que la
operación desplazada quede registrada y visible, y eso se cumple.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.errores import ValorInvalido
from rasero.persistencia.modelos import OperacionPendiente
from rasero.servicios import conteos as servicio_conteos
from rasero.servicios import senales as servicio_senales
from rasero.servicios import traspasos as servicio_traspasos
from rasero.servicios import ventas as servicio_ventas


@dataclass
class OperacionEntrante:
    id_operacion_pendiente: str
    tipo_operacion: str
    carga: dict
    recurso_afectado: str
    marca_tiempo_origen: datetime


_TIPOS = {
    "venta",
    "consulta_no_atendida",
    "anulacion_venta",
    "recepcion_traspaso",
    "resolucion_conteo",
}


def _aplicar(sesion: Session, op: OperacionPendiente) -> None:
    """Materializa el efecto de negocio de una operación ganadora despachando su `carga`."""
    carga = op.carga
    marca = op.marca_tiempo_origen

    if op.tipo_operacion == "venta":
        servicio_ventas.registrar_venta(
            sesion,
            clave_idempotencia=carga["clave_idempotencia"],
            id_turno=carga["id_turno"],
            referencia_terminal_pago=carga.get("referencia_terminal_pago"),
            instante_origen=marca,
            renglones=[
                servicio_ventas.RenglonEntrada(
                    id_producto=r["id_producto"],
                    cantidad_unidades=r.get("cantidad_unidades"),
                    cantidad_gramos=r.get("cantidad_gramos"),
                )
                for r in carga["renglones"]
            ],
        )
    elif op.tipo_operacion == "consulta_no_atendida":
        servicio_senales.registrar_consulta_no_atendida(
            sesion,
            id_producto=carga["id_producto"],
            id_turno=carga["id_turno"],
            instante_origen=marca,
        )
    elif op.tipo_operacion == "anulacion_venta":
        servicio_ventas.anular_venta(
            sesion,
            id_venta=carga["id_venta"],
            id_operador_ejecuta=carga["id_operador"],
            motivo=carga.get("motivo"),
        )
    elif op.tipo_operacion == "recepcion_traspaso":
        servicio_traspasos.recibir_traspaso(
            sesion,
            id_traspaso=carga["id_traspaso"],
            renglones=[
                servicio_traspasos.RenglonRecepcion(
                    id_producto=r["id_producto"], cantidad_recibida=r["cantidad_recibida"]
                )
                for r in carga["renglones"]
            ],
        )
    elif op.tipo_operacion == "resolucion_conteo":
        servicio_conteos.resolver_conteo(
            sesion,
            id_conteo_fisico=carga["id_conteo_fisico"],
            renglones=[
                servicio_conteos.RenglonContado(
                    id_producto=r["id_producto"],
                    id_lote=r.get("id_lote"),
                    cantidad_contada=r["cantidad_contada"],
                )
                for r in carga["renglones"]
            ],
        )


def sincronizar(
    sesion: Session, *, operaciones: list[OperacionEntrante]
) -> list[OperacionPendiente]:
    if not operaciones:
        raise ValorInvalido("El lote de sincronización no puede estar vacío.")
    for op in operaciones:
        if op.tipo_operacion not in _TIPOS:
            raise ValorInvalido(f"Tipo de operación desconocido: {op.tipo_operacion}.")

    en_orden = sorted(operaciones, key=lambda o: o.marca_tiempo_origen)
    ahora = datetime.now(timezone.utc)
    resultado: list[OperacionPendiente] = []

    for entrante in en_orden:
        fila = OperacionPendiente(
            id_operacion_pendiente=entrante.id_operacion_pendiente,
            tipo_operacion=entrante.tipo_operacion,
            carga=entrante.carga,
            recurso_afectado=entrante.recurso_afectado,
            marca_tiempo_origen=entrante.marca_tiempo_origen,
            instante_recepcion=ahora,
            estado="pendiente_de_sincronizar",
        )
        sesion.add(fila)
        sesion.flush()

        prevaleciente = sesion.execute(
            select(OperacionPendiente)
            .where(
                OperacionPendiente.recurso_afectado == entrante.recurso_afectado,
                OperacionPendiente.estado == "sincronizada",
                OperacionPendiente.id_operacion_pendiente != fila.id_operacion_pendiente,
            )
            .order_by(OperacionPendiente.marca_tiempo_origen.asc())
            .limit(1)
        ).scalar_one_or_none()

        if prevaleciente is not None and prevaleciente.marca_tiempo_origen <= fila.marca_tiempo_origen:
            # La que llega es más nueva (o igual): pierde y queda visible como conflicto resuelto.
            fila.estado = "conflicto_resuelto"
            fila.id_operacion_prevaleciente = prevaleciente.id_operacion_pendiente
            sesion.flush()
            resultado.append(fila)
            continue

        if prevaleciente is not None:
            # La que llega es más antigua: desplaza a la ya sincronizada, que permanece visible.
            prevaleciente.estado = "conflicto_resuelto"
            prevaleciente.id_operacion_prevaleciente = fila.id_operacion_pendiente
            sesion.flush()

        _aplicar(sesion, fila)
        fila.estado = "sincronizada"
        sesion.flush()
        resultado.append(fila)

    sesion.commit()
    for fila in resultado:
        sesion.refresh(fila)
    return resultado


def operacion_a_respuesta(op: OperacionPendiente) -> dict:
    return {
        "id_operacion_pendiente": str(op.id_operacion_pendiente),
        "tipo_operacion": op.tipo_operacion,
        "carga": op.carga,
        "recurso_afectado": op.recurso_afectado,
        "marca_tiempo_origen": op.marca_tiempo_origen,
        "instante_recepcion": op.instante_recepcion,
        "estado": op.estado,
        "id_operacion_prevaleciente": (
            None
            if op.id_operacion_prevaleciente is None
            else str(op.id_operacion_prevaleciente)
        ),
    }
