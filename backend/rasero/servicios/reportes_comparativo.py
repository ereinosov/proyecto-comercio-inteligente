"""Comparativo entre sucursales (008-reportes-inteligencia, User Story 1).

Solo lectura sobre 001/003/006: suma y promedia lo que esos módulos ya registraron, una
columna por sucursal activa o con actividad en el período. Cada valor coincide con el agregado
calculable a mano de los datos de origen (SC-002).

`estado_fuga` / detalle de cliente NO se tocan aquí — este comparativo es de ventas/margen/merma.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import (
    AnulacionVenta,
    Arqueo,
    MargenCalculado,
    RenglonVenta,
    Sucursal,
    Turno,
    Venta,
)
from rasero.servicios import reportes_cache
from rasero.servicios.mermas import resumen_mermas_por_causa

_TIPO = "comparativo"

# Filas del comparativo. `mejor` = "max" (más alto es mejor) o "min" (más bajo es mejor).
_INDICADORES = (
    ("ventas", "Ventas totales", "max", "moneda"),
    ("tickets", "Tickets", "max", "entero"),
    ("ticket_promedio", "Ticket promedio", "max", "moneda"),
    ("margen_ponderado", "Margen promedio ponderado", "max", "porcentaje"),
    ("merma_valorada", "Merma valorada", "min", "moneda"),
    ("diferencia_arqueo", "Diferencia de arqueo acumulada", "max", "moneda"),
)


def _ventana_utc(zona: str, ini: date, fin: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(zona)
    desde = datetime(ini.year, ini.month, ini.day, tzinfo=tz).astimezone(ZoneInfo("UTC"))
    f = fin + timedelta(days=1)
    hasta = datetime(f.year, f.month, f.day, tzinfo=tz).astimezone(ZoneInfo("UTC"))
    return desde, hasta


def _fmt(clave: str, valor: Decimal | None) -> str | None:
    if valor is None:
        return None
    if clave == "porcentaje":
        return f"{valor * 100:.1f}%"
    if clave == "entero":
        return str(int(valor))
    return f"{valor:.2f}"


def _metricas_sucursal(sesion: Session, s: Sucursal, ini: date, fin: date) -> dict:
    desde, hasta = _ventana_utc(s.zona_horaria, ini, fin)

    # Ventas y tickets: ventas NO anuladas del período, por la sucursal del turno.
    ventas_q = (
        select(
            func.coalesce(func.sum(Venta.total), 0),
            func.count(Venta.id_venta),
        )
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .outerjoin(AnulacionVenta, AnulacionVenta.id_venta == Venta.id_venta)
        .where(
            Turno.id_sucursal == s.id_sucursal,
            Venta.instante >= desde,
            Venta.instante < hasta,
            AnulacionVenta.id_anulacion_venta.is_(None),
        )
    )
    total_ventas, n_tickets = sesion.execute(ventas_q).one()
    total_ventas = Decimal(total_ventas)
    hay_ventas = n_tickets > 0

    ticket_promedio = (total_ventas / n_tickets) if hay_ventas else None

    # Margen ponderado: margen vigente que 003 ya cacheó en `margen_calculado` (lectura pura,
    # NO se dispara su recálculo), ponderado por el importe vendido de cada producto en el
    # período. Aproximación documentada (margen actual × volumen del período).
    margen_map = dict(
        sesion.execute(
            select(MargenCalculado.id_producto, MargenCalculado.margen).where(
                MargenCalculado.id_sucursal == s.id_sucursal,
                MargenCalculado.margen.is_not(None),
            )
        ).all()
    )
    importes_q = (
        select(RenglonVenta.id_producto, func.coalesce(func.sum(RenglonVenta.importe), 0))
        .join(Venta, Venta.id_venta == RenglonVenta.id_venta)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .outerjoin(AnulacionVenta, AnulacionVenta.id_venta == Venta.id_venta)
        .where(
            Turno.id_sucursal == s.id_sucursal,
            Venta.instante >= desde,
            Venta.instante < hasta,
            AnulacionVenta.id_anulacion_venta.is_(None),
        )
        .group_by(RenglonVenta.id_producto)
    )
    num = Decimal(0)
    den = Decimal(0)
    for id_producto, importe in sesion.execute(importes_q).all():
        m = margen_map.get(id_producto)
        if m is not None:
            num += Decimal(importe) * Decimal(m)
            den += Decimal(importe)
    margen_ponderado = (num / den) if den > 0 else None

    # Merma valorada del período (006, agregada por semana → se suman todas las causas).
    merma = Decimal(0)
    tiene_merma = False
    for semana in resumen_mermas_por_causa(
        sesion, id_sucursal=s.id_sucursal, desde=ini, hasta=fin
    ):
        for clave, val in semana.items():
            if clave not in ("periodo", "sin_valor"):
                merma += Decimal(str(val))
                tiene_merma = True

    # Diferencia de arqueo acumulada del período (006).
    dif_arqueo, n_arqueos = sesion.execute(
        select(func.coalesce(func.sum(Arqueo.diferencia), 0), func.count(Arqueo.id_arqueo)).where(
            Arqueo.id_sucursal == s.id_sucursal,
            Arqueo.dia_local >= ini,
            Arqueo.dia_local <= fin,
        )
    ).one()

    return {
        "ventas": total_ventas if hay_ventas else None,
        "tickets": Decimal(n_tickets) if hay_ventas else None,
        "ticket_promedio": ticket_promedio,
        "margen_ponderado": margen_ponderado,
        "merma_valorada": merma if tiene_merma else None,
        "diferencia_arqueo": Decimal(dif_arqueo) if n_arqueos else None,
    }


def _diferencia_relativa(clave_fmt: str, valor: Decimal, mejor_valor: Decimal, nombre_mejor: str) -> tuple[str | None, bool]:
    if valor == mejor_valor:
        return None, False
    if clave_fmt == "porcentaje":
        pp = (valor - mejor_valor) * 100
        return f"{pp:+.1f} pp vs. {nombre_mejor}", True
    if mejor_valor != 0:
        pct = (valor - mejor_valor) / abs(mejor_valor) * 100
        return f"{pct:+.0f}% vs. {nombre_mejor}", True
    return f"{valor - mejor_valor:+.2f} vs. {nombre_mejor}", True


def armar_indicadores(visibles: list[dict]) -> tuple[bool, list[dict]]:
    """Función pura: `visibles` = [{id_sucursal, nombre, activa, metricas: {clave: Decimal|None}}].
    Devuelve (`comparable`, `indicadores`). `comparable` es False con una sola sucursal; sin
    columna de contraste ni `diferencia_relativa` en ese caso (FR-008).
    """
    comparable = len(visibles) > 1
    filas = []
    for clave, etiqueta, mejor, clave_fmt in _INDICADORES:
        presentes = [
            (s, s["metricas"][clave]) for s in visibles if s["metricas"][clave] is not None
        ]
        mejor_valor = None
        nombre_mejor = None
        if comparable and presentes:
            s_mejor, mejor_valor = (max if mejor == "max" else min)(presentes, key=lambda p: p[1])
            nombre_mejor = s_mejor["nombre"]

        celdas = []
        for s in visibles:
            valor = s["metricas"][clave]
            dif, atencion = (None, False)
            if comparable and valor is not None and mejor_valor is not None and s["nombre"] != nombre_mejor:
                dif, atencion = _diferencia_relativa(clave_fmt, valor, mejor_valor, nombre_mejor)
            celdas.append(
                {
                    "id_sucursal": s["id_sucursal"],
                    "valor": _fmt(clave_fmt, valor),
                    "sin_datos": valor is None,
                    "diferencia_relativa": dif,
                    "atencion": atencion,
                }
            )
        filas.append({"clave": clave, "etiqueta": etiqueta, "celdas": celdas})
    return comparable, filas


def _construir(sesion: Session, ini: date, fin: date) -> dict:
    sucursales = sesion.execute(select(Sucursal).order_by(Sucursal.id_sucursal)).scalars().all()
    metricas = {s.id_sucursal: _metricas_sucursal(sesion, s, ini, fin) for s in sucursales}

    # Una sucursal entra si está activa O tuvo actividad (ventas / merma / arqueo) en el período.
    visibles = [
        {
            "id_sucursal": s.id_sucursal,
            "nombre": s.nombre,
            "activa": s.activo,
            "metricas": metricas[s.id_sucursal],
        }
        for s in sucursales
        if s.activo or any(v is not None for v in metricas[s.id_sucursal].values())
    ]
    comparable, filas = armar_indicadores(visibles)

    return {
        "periodo_inicio": ini.isoformat(),
        "periodo_fin": fin.isoformat(),
        "comparable": comparable,
        "sucursales": [
            {"id_sucursal": s["id_sucursal"], "nombre": s["nombre"], "activa": s["activa"]}
            for s in visibles
        ],
        "indicadores": filas,
    }


def comparativo(
    sesion: Session, *, periodo_inicio: date, periodo_fin: date, actualizar: bool = False
) -> dict:
    clave = dict(
        tipo=_TIPO,
        ambito_sucursal=None,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        granularidad="total",
    )
    if not actualizar:
        cacheado = reportes_cache.leer(sesion, **clave)
        if cacheado is not None:
            return {**cacheado["contenido"], "instante_calculo": cacheado["instante_calculo"].isoformat()}

    contenido = _construir(sesion, periodo_inicio, periodo_fin)
    instante = reportes_cache.guardar(sesion, **clave, contenido=contenido)
    sesion.commit()
    return {**contenido, "instante_calculo": instante.isoformat()}
