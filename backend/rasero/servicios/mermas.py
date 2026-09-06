"""Servicio de mermas (006-caja-mermas-fraude, US2 — T023, T024).

- `clasificar_merma` — dos ramas (research.md #5, #10):
  - **sin `id_conteo_renglon`** (✓): declaración de merma fuera de conteo (rotura, vencimiento en
    estantería, FR-012). Valora al costo del lote FEFO de 001; marca `conciliar_con_conteo = true`.
    NUNCA escribe en `existencia`/`movimiento_inventario` (FR-034).
  - **con `id_conteo_renglon`** (001 User Story 5 ya implementada, T065-T071): clasifica la
    `diferencia` bruta que `001` expone en esa línea de conteo **sin recalcularla** (FR-033); el
    ajuste de existencia ya lo hizo `001` al resolver el conteo, así que `conciliar_con_conteo =
    false`. El período de atribución va entre el conteo anterior resuelto de la sucursal y este
    (FR-011).
- `alertas_caducidad` — consulta DERIVADA sobre `lote`/`existencia` de 001 (FR-014). Informativa:
  006 NO da de baja, descuenta ni traspasa nada.
- `listar_mermas` — desglose por causa/producto/sucursal (FR-016); exige `id_sucursal` (FR-038).

Una merma NUNCA lleva un `id_operador` de imputación (FR-011); `id_operador_registro` es sólo
quién hizo el registro administrativo.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.config import caja as cfg
from rasero.dominio.merma import periodo_entre_conteos, valorar_merma
from rasero.dominio.seleccion_lote import ordenar_fefo
from rasero.errores import ErrorCaja
from rasero.persistencia.modelos import (
    ConteoFisico,
    ConteoRenglon,
    Existencia,
    Lote,
    Merma,
    Producto,
    Sucursal,
)

_CAUSAS = {
    "vencimiento",
    "dano",
    "robo_externo",
    "error_conteo",
    "merma_granel",
    "pendiente_clasificar",
}
_GRAMOS_POR_KILOGRAMO = Decimal("1000")


def _dia_local_sucursal(sucursal: Sucursal) -> date:
    return datetime.now(ZoneInfo(sucursal.zona_horaria)).date()


def _sucursal_o_404(sesion: Session, id_sucursal: int) -> Sucursal:
    sucursal = sesion.get(Sucursal, id_sucursal)
    if sucursal is None:
        raise ErrorCaja(
            "caja_sucursal_no_existe", "Esa sucursal no existe.", status_code=404
        )
    return sucursal


def _costo_por_unidad_de_cantidad(lote: Lote | None, producto: Producto) -> Decimal | None:
    """El costo del lote está por unidad, o por kilogramo si el producto es granel. La
    `cantidad_faltante` de una merma de granel está en gramos, así que el costo se divide entre
    1000 para quedar en la misma base (por gramo). Si no hay lote con costo, `None` ("no
    calculable", FR-010).
    """
    if lote is None:
        return None
    if producto.es_granel:
        return Decimal(lote.costo_unitario) / _GRAMOS_POR_KILOGRAMO
    return Decimal(lote.costo_unitario)


def _lote_fefo(sesion: Session, *, id_producto: int, id_sucursal: int) -> Lote | None:
    lotes = list(
        sesion.execute(
            select(Lote).where(
                Lote.id_producto == id_producto, Lote.id_sucursal == id_sucursal
            )
        ).scalars()
    )
    if not lotes:
        return None
    return ordenar_fefo(lotes)[0]


def clasificar_merma(
    sesion: Session,
    *,
    id_producto: int,
    id_sucursal: int,
    cantidad_faltante,
    causa: str,
    id_operador_registro: int,
    id_conteo_renglon: int | None = None,
    id_lote: int | None = None,
    nota: str | None = None,
) -> Merma:
    if causa not in _CAUSAS:
        raise ErrorCaja(
            "caja_causa_invalida",
            "Esa causa de merma no es válida. Elige vencimiento, daño, robo externo, error de "
            "conteo, merma de granel o pendiente de clasificar.",
        )
    try:
        cantidad = Decimal(str(cantidad_faltante))
    except Exception:
        raise ErrorCaja("caja_cantidad_invalida", "La cantidad faltante no es un número válido.")
    if cantidad <= 0:
        raise ErrorCaja(
            "caja_cantidad_invalida", "La cantidad faltante debe ser mayor que cero."
        )
    cantidad = cantidad.quantize(Decimal("1"))

    producto = sesion.get(Producto, id_producto)
    if producto is None:
        raise ErrorCaja(
            "caja_producto_no_existe", "Ese producto no existe.", status_code=404
        )
    sucursal = _sucursal_o_404(sesion, id_sucursal)

    if id_conteo_renglon is not None:
        return _clasificar_diferencia_de_conteo(
            sesion,
            renglon_id=id_conteo_renglon,
            producto=producto,
            sucursal=sucursal,
            cantidad=cantidad,
            causa=causa,
            id_operador_registro=id_operador_registro,
            id_lote=id_lote,
            nota=nota,
        )

    lote: Lote | None
    if id_lote is not None:
        lote = sesion.get(Lote, id_lote)
        if lote is None:
            raise ErrorCaja(
                "caja_lote_no_existe", "Ese lote no existe.", status_code=404
            )
    else:
        lote = _lote_fefo(sesion, id_producto=id_producto, id_sucursal=id_sucursal)

    costo = _costo_por_unidad_de_cantidad(lote, producto)
    valoracion = valorar_merma(cantidad, costo)

    dia = _dia_local_sucursal(sucursal)
    periodo_desde, periodo_hasta = periodo_entre_conteos(
        fecha_conteo_actual=None, fecha_conteo_anterior=None, fecha_declaracion=dia
    )
    estado = "clasificada" if causa != "pendiente_clasificar" else "pendiente_clasificar"

    merma = Merma(
        id_conteo_renglon=None,
        id_producto=id_producto,
        id_lote=lote.id_lote if lote is not None else None,
        id_sucursal=id_sucursal,
        cantidad_faltante=cantidad,
        causa=causa,
        valoracion=valoracion,
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        estado=estado,
        # Merma declarada fuera de conteo: 001 ajustará `existencia` en el próximo conteo (FR-034).
        conciliar_con_conteo=True,
        id_operador_registro=id_operador_registro,
        instante_registro=datetime.now(timezone.utc),
        nota=nota,
    )
    sesion.add(merma)
    sesion.flush()
    return merma


def _fecha_local(instante, zona_horaria: str) -> date:
    return instante.astimezone(ZoneInfo(zona_horaria)).date()


def _fecha_conteo_anterior(
    sesion: Session, *, id_sucursal: int, conteo: ConteoFisico
) -> date | None:
    """Fecha de resolución del conteo resuelto de la sucursal inmediatamente anterior a `conteo`
    (mismo alcance no se distingue aquí: `001` acota el conteo, no `006`).
    """
    referencia = conteo.instante_resolucion or conteo.instante_inicio
    anterior = sesion.execute(
        select(ConteoFisico)
        .where(
            ConteoFisico.id_sucursal == id_sucursal,
            ConteoFisico.estado == "resuelto",
            ConteoFisico.id_conteo_fisico != conteo.id_conteo_fisico,
            ConteoFisico.instante_resolucion < referencia,
        )
        .order_by(ConteoFisico.instante_resolucion.desc())
        .limit(1)
    ).scalar_one_or_none()
    if anterior is None:
        return None
    sucursal = sesion.get(Sucursal, id_sucursal)
    return _fecha_local(anterior.instante_resolucion, sucursal.zona_horaria)


def _clasificar_diferencia_de_conteo(
    sesion: Session,
    *,
    renglon_id: int,
    producto: Producto,
    sucursal: Sucursal,
    cantidad: Decimal,
    causa: str,
    id_operador_registro: int,
    id_lote: int | None,
    nota: str | None,
) -> Merma:
    renglon = sesion.get(ConteoRenglon, renglon_id)
    if renglon is None:
        raise ErrorCaja(
            "caja_conteo_renglon_no_existe", "Esa línea de conteo no existe.", status_code=404
        )
    if renglon.id_producto != producto.id_producto:
        raise ErrorCaja(
            "caja_conteo_renglon_otro_producto",
            "Esa línea de conteo es de otro producto; revisa el id_producto.",
        )

    # La diferencia bruta la fija `001`; `006` la clasifica, no la recalcula (FR-033).
    faltante_bruto = -Decimal(renglon.diferencia)
    if faltante_bruto <= 0:
        raise ErrorCaja(
            "caja_conteo_sin_faltante",
            "Esa línea de conteo no tiene un faltante que clasificar: su diferencia no es negativa.",
        )
    if cantidad > faltante_bruto:
        raise ErrorCaja(
            "caja_cantidad_excede_faltante",
            f"La cantidad a clasificar ({cantidad}) no puede exceder el faltante bruto que "
            f"expone el conteo ({faltante_bruto}).",
        )

    conteo = sesion.get(ConteoFisico, renglon.id_conteo_fisico)

    lote_id = renglon.id_lote if renglon.id_lote is not None else id_lote
    if lote_id is not None:
        lote = sesion.get(Lote, lote_id)
        if lote is None:
            raise ErrorCaja("caja_lote_no_existe", "Ese lote no existe.", status_code=404)
    else:
        lote = _lote_fefo(
            sesion, id_producto=producto.id_producto, id_sucursal=sucursal.id_sucursal
        )

    costo = _costo_por_unidad_de_cantidad(lote, producto)
    valoracion = valorar_merma(cantidad, costo)

    fecha_conteo = _fecha_local(
        conteo.instante_resolucion or conteo.instante_inicio, sucursal.zona_horaria
    )
    fecha_anterior = _fecha_conteo_anterior(
        sesion, id_sucursal=sucursal.id_sucursal, conteo=conteo
    )
    periodo_desde, periodo_hasta = periodo_entre_conteos(
        fecha_conteo_actual=fecha_conteo,
        fecha_conteo_anterior=fecha_anterior,
        fecha_declaracion=fecha_conteo,
    )
    estado = "clasificada" if causa != "pendiente_clasificar" else "pendiente_clasificar"

    merma = Merma(
        id_conteo_renglon=renglon_id,
        id_producto=producto.id_producto,
        id_lote=lote.id_lote if lote is not None else None,
        id_sucursal=sucursal.id_sucursal,
        cantidad_faltante=cantidad,
        causa=causa,
        valoracion=valoracion,
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        estado=estado,
        # El ajuste de existencia ya lo hizo `001` al resolver el conteo (FR-032 de 001).
        conciliar_con_conteo=False,
        id_operador_registro=id_operador_registro,
        instante_registro=datetime.now(timezone.utc),
        nota=nota,
    )
    sesion.add(merma)
    sesion.flush()
    return merma


def listar_mermas(
    sesion: Session,
    *,
    id_sucursal: int,
    causa: str | None = None,
    id_producto: int | None = None,
    desde=None,
    hasta=None,
) -> dict:
    if id_sucursal is None:
        raise ErrorCaja(
            "caja_sucursal_requerida",
            "Indica una sucursal para consultar sus mermas (no se mezclan sucursales).",
        )
    consulta = select(Merma).where(Merma.id_sucursal == id_sucursal)
    if causa is not None:
        consulta = consulta.where(Merma.causa == causa)
    if id_producto is not None:
        consulta = consulta.where(Merma.id_producto == id_producto)
    if desde is not None:
        consulta = consulta.where(Merma.periodo_hasta >= desde)
    if hasta is not None:
        consulta = consulta.where(Merma.periodo_hasta <= hasta)
    consulta = consulta.order_by(Merma.periodo_hasta.desc(), Merma.id_merma.desc())
    mermas = list(sesion.execute(consulta).scalars())

    total = sum((Decimal(m.valoracion) for m in mermas if m.valoracion is not None), Decimal("0"))
    no_calculables = sum(1 for m in mermas if m.valoracion is None)
    return {
        "total_valorado": str(total.quantize(Decimal("0.01"))),
        "con_valor_no_calculable": no_calculables,
        "mermas": [merma_a_respuesta(m) for m in mermas],
    }


def alertas_caducidad(
    sesion: Session, *, id_sucursal: int, dentro_de_dias: int | None = None
) -> list[dict]:
    if id_sucursal is None:
        raise ErrorCaja(
            "caja_sucursal_requerida",
            "Indica una sucursal para consultar sus alertas de caducidad.",
        )
    sucursal = _sucursal_o_404(sesion, id_sucursal)
    ventana = dentro_de_dias if dentro_de_dias is not None else cfg.VENTANA_ALERTA_CADUCIDAD_DIAS
    hoy = _dia_local_sucursal(sucursal)
    limite = hoy + timedelta(days=ventana)

    existencia_por_lote = dict(
        sesion.execute(
            select(Existencia.id_lote, func.sum(Existencia.cantidad))
            .where(Existencia.id_sucursal == id_sucursal, Existencia.id_lote.is_not(None))
            .group_by(Existencia.id_lote)
        ).all()
    )

    filas = sesion.execute(
        select(Lote, Producto.nombre)
        .join(Producto, Producto.id_producto == Lote.id_producto)
        .where(
            Lote.id_sucursal == id_sucursal,
            Lote.fecha_caducidad.is_not(None),
            Lote.fecha_caducidad <= limite,
        )
        .order_by(Lote.fecha_caducidad)
    ).all()

    alertas: list[dict] = []
    for lote, nombre in filas:
        restante = existencia_por_lote.get(lote.id_lote, Decimal("0")) or Decimal("0")
        if restante <= 0:
            continue
        valor_en_riesgo = (
            str((Decimal(restante) * Decimal(lote.costo_unitario)).quantize(Decimal("0.01")))
            if lote.costo_unitario is not None
            else None
        )
        alertas.append(
            {
                "id_lote": lote.id_lote,
                "id_producto": lote.id_producto,
                "nombre_producto": nombre,
                "id_sucursal": id_sucursal,
                "fecha_caducidad": lote.fecha_caducidad.isoformat(),
                "dias_para_caducar": (lote.fecha_caducidad - hoy).days,
                "ya_caducado": lote.fecha_caducidad < hoy,
                "existencia_restante": int(restante),
                "valor_en_riesgo": valor_en_riesgo,
            }
        )
    return alertas


def obtener_merma(sesion: Session, *, id_merma: int) -> Merma:
    merma = sesion.get(Merma, id_merma)
    if merma is None:
        raise ErrorCaja("caja_merma_no_existe", "Esa merma no existe.", status_code=404)
    return merma


def merma_a_respuesta(merma: Merma) -> dict:
    return {
        "id_merma": merma.id_merma,
        "id_conteo_renglon": merma.id_conteo_renglon,
        "id_producto": merma.id_producto,
        "id_lote": merma.id_lote,
        "id_sucursal": merma.id_sucursal,
        "cantidad_faltante": int(merma.cantidad_faltante),
        "causa": merma.causa,
        "valoracion": str(merma.valoracion) if merma.valoracion is not None else None,
        "moneda": merma.moneda,
        "periodo_desde": merma.periodo_desde.isoformat(),
        "periodo_hasta": merma.periodo_hasta.isoformat(),
        "estado": merma.estado,
        "conciliar_con_conteo": merma.conciliar_con_conteo,
        "id_operador_registro": merma.id_operador_registro,
        "instante_registro": merma.instante_registro.isoformat(),
        "nota": merma.nota,
    }
