"""Tendencias multi-semana / mes (008-reportes-inteligencia, User Story 2).

Agrega, por período LOCAL de la sucursal (semana ISO o mes calendario), las series que
001/003/004/006 ya producen — nunca recalculando su lógica de origen. Ámbito "todas las
sucursales" = SUMA por período, no promedio (FR-012). Los períodos parciales de los bordes se
marcan `completo=False` (FR-011).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.config.reportes import PERIODOS_TENDENCIA_DEFECTO
from rasero.dominio.periodo_local import Periodo, periodos_locales
from rasero.persistencia.modelos import (
    AnulacionVenta,
    DemandaCorregida,
    MargenCalculado,
    Merma,
    RenglonVenta,
    Sucursal,
    Turno,
    Venta,
)
from rasero.servicios import reportes_cache

_INDICADORES = ("ventas", "unidades", "margen_ponderado", "merma_valorada", "demanda_producto")


def _sucursales(sesion: Session, id_sucursal: int | None) -> list[Sucursal]:
    q = select(Sucursal).order_by(Sucursal.id_sucursal)
    if id_sucursal is not None:
        q = q.where(Sucursal.id_sucursal == id_sucursal)
    return list(sesion.execute(q).scalars().all())


def _ventas_periodo(sesion: Session, s: Sucursal, p: Periodo, *, contar_unidades: bool):
    """(monto, unidades) de ventas NO anuladas de la sucursal en el período."""
    base = (
        select(RenglonVenta.importe, RenglonVenta.cantidad_unidades, RenglonVenta.cantidad_gramos)
        .join(Venta, Venta.id_venta == RenglonVenta.id_venta)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .outerjoin(AnulacionVenta, AnulacionVenta.id_venta == Venta.id_venta)
        .where(
            Turno.id_sucursal == s.id_sucursal,
            Venta.instante >= p.inicio_utc,
            Venta.instante < p.fin_utc,
            AnulacionVenta.id_anulacion_venta.is_(None),
        )
    )
    monto = Decimal(0)
    unidades = Decimal(0)
    for importe, cu, cg in sesion.execute(base).all():
        monto += Decimal(importe)
        if contar_unidades:
            unidades += Decimal(cu) if cu is not None else (Decimal(cg) / 1000 if cg else Decimal(0))
    return monto, unidades


def _margen_ponderado_periodo(sesion: Session, s: Sucursal, p: Periodo) -> Decimal | None:
    margen_map = dict(
        sesion.execute(
            select(MargenCalculado.id_producto, MargenCalculado.margen).where(
                MargenCalculado.id_sucursal == s.id_sucursal, MargenCalculado.margen.is_not(None)
            )
        ).all()
    )
    filas = sesion.execute(
        select(RenglonVenta.id_producto, func.coalesce(func.sum(RenglonVenta.importe), 0))
        .join(Venta, Venta.id_venta == RenglonVenta.id_venta)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .outerjoin(AnulacionVenta, AnulacionVenta.id_venta == Venta.id_venta)
        .where(
            Turno.id_sucursal == s.id_sucursal,
            Venta.instante >= p.inicio_utc,
            Venta.instante < p.fin_utc,
            AnulacionVenta.id_anulacion_venta.is_(None),
        )
        .group_by(RenglonVenta.id_producto)
    ).all()
    num = den = Decimal(0)
    for id_producto, importe in filas:
        m = margen_map.get(id_producto)
        if m is not None:
            num += Decimal(importe) * Decimal(m)
            den += Decimal(importe)
    return (num / den) if den > 0 else None


def _merma_periodo(sesion: Session, s: Sucursal, p: Periodo) -> Decimal | None:
    total, n = sesion.execute(
        select(func.coalesce(func.sum(Merma.valoracion), 0), func.count(Merma.id_merma)).where(
            Merma.id_sucursal == s.id_sucursal,
            Merma.causa != "pendiente_clasificar",
            Merma.periodo_hasta >= p.inicio_local,
            Merma.periodo_hasta < (p.fin_utc.date()),
        )
    ).one()
    return Decimal(total) if n else None


def _demanda_periodo(sesion: Session, s: Sucursal, p: Periodo, id_producto: int) -> Decimal | None:
    total, n = sesion.execute(
        select(func.coalesce(func.sum(DemandaCorregida.valor), 0), func.count()).where(
            DemandaCorregida.id_sucursal == s.id_sucursal,
            DemandaCorregida.id_producto == id_producto,
            DemandaCorregida.periodo >= p.inicio_local,
            DemandaCorregida.periodo < p.fin_utc.date(),
            DemandaCorregida.censura_total.is_(False),
        )
    ).one()
    return Decimal(total) if n else None


def _construir(
    sesion: Session,
    *,
    indicador: str,
    granularidad: str,
    id_sucursal: int | None,
    id_producto: int | None,
    periodos: int,
) -> dict:
    sucursales = _sucursales(sesion, id_sucursal)
    if not sucursales:
        return {"disponible": False, "razon": "no hay sucursales para el ámbito pedido", "puntos": []}

    if indicador == "demanda_producto":
        if id_producto is None:
            return {"disponible": False, "razon": "falta id_producto para la demanda", "puntos": []}
        # ¿004 materializó alguna serie para este producto en el ámbito?
        hay = sesion.execute(
            select(func.count()).select_from(DemandaCorregida).where(
                DemandaCorregida.id_producto == id_producto,
                *([DemandaCorregida.id_sucursal == id_sucursal] if id_sucursal else []),
            )
        ).scalar_one()
        if not hay:
            return {
                "disponible": False,
                "razon": "el producto no tiene una serie de demanda corregida (004) para el ámbito",
                "puntos": [],
            }

    # La zona horaria de referencia: la de la primera sucursal (dos tiendas en la misma zona hoy).
    rejilla = periodos_locales(sucursales[0].zona_horaria, granularidad, periodos)
    puntos = []
    for p in rejilla:
        valor = Decimal(0)
        alguno = False
        for s in sucursales:
            if indicador == "ventas":
                v, _ = _ventas_periodo(sesion, s, p, contar_unidades=False)
                valor += v
                alguno = True
            elif indicador == "unidades":
                _, u = _ventas_periodo(sesion, s, p, contar_unidades=True)
                valor += u
                alguno = True
            elif indicador == "merma_valorada":
                m = _merma_periodo(sesion, s, p)
                if m is not None:
                    valor += m
                    alguno = True
            elif indicador == "demanda_producto":
                d = _demanda_periodo(sesion, s, p, id_producto)
                if d is not None:
                    valor += d
                    alguno = True
            elif indicador == "margen_ponderado":
                # No se suma entre sucursales: se pondera globalmente. Se recalcula abajo.
                pass
        if indicador == "margen_ponderado":
            num = den = Decimal(0)
            for s in sucursales:
                mp = _margen_ponderado_periodo(sesion, s, p)
                v_s, _ = _ventas_periodo(sesion, s, p, contar_unidades=False)
                if mp is not None and v_s > 0:
                    num += mp * v_s
                    den += v_s
            valor = (num / den) if den > 0 else Decimal(0)
            alguno = den > 0

        puntos.append(
            {
                "periodo": p.inicio_local.isoformat(),
                "etiqueta": p.etiqueta,
                "valor": (f"{valor * 100:.1f}%" if indicador == "margen_ponderado" else f"{valor:.2f}")
                if alguno
                else None,
                "completo": p.completo,
            }
        )

    return {"disponible": True, "razon": None, "puntos": puntos}


def tendencia(
    sesion: Session,
    *,
    indicador: str,
    granularidad: str,
    id_sucursal: int | None = None,
    id_producto: int | None = None,
    periodos: int | None = None,
    actualizar: bool = False,
) -> dict:
    if indicador not in _INDICADORES:
        return {"indicador": indicador, "granularidad": granularidad, "ambito": "todas",
                "disponible": False, "razon": "indicador desconocido", "puntos": [],
                "instante_calculo": None}
    if granularidad not in ("semana", "mes"):
        return {"indicador": indicador, "granularidad": granularidad, "ambito": "todas",
                "disponible": False, "razon": "granularidad desconocida", "puntos": [],
                "instante_calculo": None}
    periodos = periodos or PERIODOS_TENDENCIA_DEFECTO[granularidad]

    sucs = _sucursales(sesion, id_sucursal)
    zona = sucs[0].zona_horaria if sucs else "UTC"
    rejilla = periodos_locales(zona, granularidad, periodos)
    ini = rejilla[0].inicio_local if rejilla else date.today()
    fin = rejilla[-1].inicio_local if rejilla else ini

    # La caché de `agregado_reporte` sólo distingue (tipo, ámbito, período, granularidad); el
    # indicador y el producto van dentro de `contenido["_clave"]`. Si el `_clave` guardado no
    # coincide con el pedido, se trata como fallo de caché y se sobrescribe (last-writer-wins;
    # aceptable — cada indicador de una vista se pide de a uno). Ver research.md §7.
    clave_cache = dict(
        tipo="tendencia", ambito_sucursal=id_sucursal,
        periodo_inicio=ini, periodo_fin=fin, granularidad=granularidad,
    )
    clave_logica = f"{indicador}|{id_producto or ''}"

    if not actualizar:
        cacheado = reportes_cache.leer(sesion, **clave_cache)
        if cacheado is not None and cacheado["contenido"].get("_clave") == clave_logica:
            c = {k: v for k, v in cacheado["contenido"].items() if k != "_clave"}
            return {**c, "instante_calculo": cacheado["instante_calculo"].isoformat()}

    cuerpo = _construir(
        sesion, indicador=indicador, granularidad=granularidad,
        id_sucursal=id_sucursal, id_producto=id_producto, periodos=periodos,
    )
    ambito = "todas" if id_sucursal is None else (sucs[0].nombre if sucs else str(id_sucursal))
    contenido = {
        "indicador": indicador, "granularidad": granularidad, "ambito": ambito,
        "_clave": clave_logica, **cuerpo,
    }
    instante = reportes_cache.guardar(sesion, **clave_cache, contenido=contenido)
    sesion.commit()
    salida = {k: v for k, v in contenido.items() if k != "_clave"}
    return {**salida, "instante_calculo": instante.isoformat()}
