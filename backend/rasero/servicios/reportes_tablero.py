"""Tablero de KPIs consolidados (008-reportes-inteligencia, User Story 3).

Una tarjeta por módulo, cada una con 2–3 cifras resumen y su propio `periodo_referencia`
(FR-014). Cada cifra coincide con lo que su módulo de origen reporta (FR-015); una tarjeta sin
base declara la razón, nunca "0" (FR-016). Solo lectura sobre 001–007.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.config.reportes import CUOTA_NO_ATENDIDA_ATENCION, MARGEN_SALUDABLE
from rasero.dominio.periodo_local import periodos_locales
from rasero.persistencia.modelos import (
    AnomaliaCaja,
    AnulacionVenta,
    Arqueo,
    ExperimentoReactivacion,
    Existencia,
    Lote,
    MargenCalculado,
    Merma,
    Sucursal,
    Turno,
    Venta,
)
from rasero.servicios import reportes_cache
from rasero.servicios.cobertura_pago import resumen_cobertura
from rasero.servicios.inventario import capital_inmovilizado
from rasero.servicios.clientes import resumen_fuga_por_segmento

_VEREDICTO = {
    "efectivo": "Efectivo",
    "no_efectivo": "No efectivo",
    "muestra_insuficiente": "Sin evidencia",
}


def _tarjeta(modulo, titulo, periodo, cifras, *, sin_datos=False, razon=None):
    return {
        "modulo": modulo,
        "titulo": titulo,
        "periodo_referencia": periodo,
        "sin_datos": sin_datos,
        "razon": razon,
        "cifras": cifras or [],
    }


def _cifra(etiqueta, valor, atencion=False):
    return {"etiqueta": etiqueta, "valor": valor, "atencion": atencion}


def _ventana_semana_utc(zona):
    p = periodos_locales(zona, "semana", 1)[0]
    return p.inicio_utc, p.fin_utc, p.etiqueta


def _ventana_mes_utc(zona):
    p = periodos_locales(zona, "mes", 1)[0]
    return p.inicio_utc, p.fin_utc, p.etiqueta


def _ventas_agg(sesion, desde, hasta, columnas):
    """`columnas` = lista de expresiones de agregación sobre `venta` no anulada del rango."""
    return sesion.execute(
        select(*columnas)
        .select_from(Venta)
        .join(Turno, Turno.id_turno == Venta.id_turno)
        .outerjoin(AnulacionVenta, AnulacionVenta.id_venta == Venta.id_venta)
        .where(
            Venta.instante >= desde,
            Venta.instante < hasta,
            AnulacionVenta.id_anulacion_venta.is_(None),
        )
    ).one()


def _construir(sesion: Session) -> dict:
    sucursales = list(sesion.execute(select(Sucursal)).scalars())
    activas = [s for s in sucursales if s.activo]
    zona = (activas[0].zona_horaria if activas else (sucursales[0].zona_horaria if sucursales else "UTC"))

    sem_ini, sem_fin, sem_lbl = _ventana_semana_utc(zona)
    mes_ini, mes_fin, mes_lbl = _ventana_mes_utc(zona)

    tarjetas = []

    # ── Ventas (001) — semana ────────────────────────────────────────────────────────────────
    total, n = _ventas_agg(
        sesion, sem_ini, sem_fin,
        [func.coalesce(func.sum(Venta.total), 0), func.count(Venta.id_venta)],
    )
    if n:
        total = Decimal(total)
        tarjetas.append(_tarjeta("ventas", "Ventas", sem_lbl, [
            _cifra("Ventas", f"{total:.2f}"),
            _cifra("Tickets", str(n)),
            _cifra("Ticket promedio", f"{total / n:.2f}"),
        ]))
    else:
        tarjetas.append(_tarjeta("ventas", "Ventas", sem_lbl, [], sin_datos=True,
                                 razon="datos insuficientes para el período"))

    # ── Márgenes (003) ──────────────────────────────────────────────────────────────────────
    margenes = sesion.execute(
        select(MargenCalculado.margen).where(MargenCalculado.margen.is_not(None))
    ).scalars().all()
    if margenes:
        bajos = sum(1 for m in margenes if Decimal(m) < Decimal(str(MARGEN_SALUDABLE)))
        tarjetas.append(_tarjeta("margenes", "Márgenes", "a hoy", [
            _cifra("Productos con margen bajo o pérdida", str(bajos), atencion=bajos > 0),
        ]))
    else:
        tarjetas.append(_tarjeta("margenes", "Márgenes", "a hoy", [], sin_datos=True,
                                 razon="003 aún no calculó ningún margen"))

    # ── Inventario (001) — a hoy ────────────────────────────────────────────────────────────
    valor_inv = sesion.execute(
        select(func.coalesce(func.sum(Existencia.cantidad * Lote.costo_unitario), 0))
        .join(Lote, Lote.id_lote == Existencia.id_lote)
        .where(Existencia.cantidad > 0)
    ).scalar_one()
    n_inmovilizado = len(capital_inmovilizado(sesion))
    tarjetas.append(_tarjeta("inventario", "Inventario", "a hoy", [
        _cifra("Valor de inventario", f"{Decimal(valor_inv):.2f}"),
        _cifra("Lotes con capital inmovilizado", str(n_inmovilizado), atencion=n_inmovilizado > 0),
    ]))

    # ── Mermas (006) — mes ─────────────────────────────────────────────────────────────────
    merma_mes, n_merma = sesion.execute(
        select(func.coalesce(func.sum(Merma.valoracion), 0), func.count(Merma.id_merma)).where(
            Merma.causa != "pendiente_clasificar",
            Merma.periodo_hasta >= mes_ini.date(),
            Merma.periodo_hasta < mes_fin.date(),
        )
    ).one()
    (ventas_mes,) = _ventas_agg(
        sesion, mes_ini, mes_fin, [func.coalesce(func.sum(Venta.total), 0)]
    )
    if n_merma:
        peso = (Decimal(merma_mes) / Decimal(ventas_mes) * 100) if Decimal(ventas_mes) > 0 else None
        cifras = [_cifra("Merma valorada", f"{Decimal(merma_mes):.2f}", atencion=Decimal(merma_mes) > 0)]
        if peso is not None:
            cifras.append(_cifra("Sobre las ventas del mes", f"{peso:.1f}%"))
        tarjetas.append(_tarjeta("mermas", "Mermas", mes_lbl, cifras))
    else:
        tarjetas.append(_tarjeta("mermas", "Mermas", mes_lbl, [], sin_datos=True,
                                 razon="sin mermas registradas en el período"))

    # ── Fraude / caja (006) — mes ──────────────────────────────────────────────────────────
    n_anomalias = sesion.execute(
        select(func.count()).select_from(AnomaliaCaja).where(
            AnomaliaCaja.estado == "sin_explicacion"
        )
    ).scalar_one()
    dif_arqueo = sesion.execute(
        select(func.coalesce(func.sum(Arqueo.diferencia), 0)).where(
            Arqueo.dia_local >= mes_ini.date(), Arqueo.dia_local < mes_fin.date()
        )
    ).scalar_one()
    tarjetas.append(_tarjeta("fraude", "Caja y fraude", mes_lbl, [
        _cifra("Anomalías abiertas", str(n_anomalias), atencion=n_anomalias > 0),
        _cifra("Diferencia de arqueo acumulada", f"{Decimal(dif_arqueo):.2f}",
               atencion=Decimal(dif_arqueo) < 0),
    ]))

    # ── Pagos (007) — mes ──────────────────────────────────────────────────────────────────
    total_no_atendida = 0
    cuota_max = Decimal(0)
    for s in activas:
        try:
            r = resumen_cobertura(sesion, id_sucursal=s.id_sucursal, desde=mes_ini.date(),
                                  hasta=(mes_fin.date()))
        except Exception:
            continue
        total_no_atendida += int(r.get("total_intencion_no_atendida", 0) or 0)
        for m in r.get("medios", []):
            c = m.get("cuota_no_atendida")
            if c is not None:
                cuota_max = max(cuota_max, Decimal(str(c)))
    tarjetas.append(_tarjeta("pagos", "Pagos", mes_lbl, [
        _cifra("Intención de compra no atendida", str(total_no_atendida), atencion=total_no_atendida > 0),
        _cifra("Cuota máxima por medio", f"{cuota_max * 100:.1f}%",
               atencion=cuota_max > Decimal(str(CUOTA_NO_ATENDIDA_ATENCION))),
    ]))

    # ── Promociones / reactivación (005) ───────────────────────────────────────────────────
    exp = sesion.execute(
        select(ExperimentoReactivacion)
        .where(ExperimentoReactivacion.instante_cierre.is_not(None))
        .order_by(ExperimentoReactivacion.instante_cierre.desc())
        .limit(1)
    ).scalar_one_or_none()
    if exp is not None:
        tarjetas.append(_tarjeta("promociones", "Reactivación", "último experimento", [
            _cifra("Veredicto", _VEREDICTO.get(exp.veredicto, exp.veredicto)),
            _cifra("Cerrado", exp.instante_cierre.date().isoformat()),
        ]))
    else:
        tarjetas.append(_tarjeta("promociones", "Reactivación", "—", [], sin_datos=True,
                                 razon="sin experimento cerrado"))

    # ── Clientes (002) ────────────────────────────────────────────────────────────────────
    fuga = resumen_fuga_por_segmento(sesion)
    en_riesgo = int(fuga.get("activa", 0)) + int(fuga.get("confirmada", 0))
    tarjetas.append(_tarjeta("clientes", "Clientes", "a hoy", [
        _cifra("Con señal de fuga (activa o confirmada)", str(en_riesgo), atencion=en_riesgo > 0),
    ]))

    return {"tarjetas": tarjetas}


def tablero(sesion: Session, *, actualizar: bool = False) -> dict:
    from datetime import date

    hoy = date.today()
    clave = dict(tipo="tablero", ambito_sucursal=None,
                 periodo_inicio=hoy, periodo_fin=hoy, granularidad="total")
    if not actualizar:
        cacheado = reportes_cache.leer(sesion, **clave)
        if cacheado is not None:
            return {**cacheado["contenido"], "instante_calculo": cacheado["instante_calculo"].isoformat()}
    contenido = _construir(sesion)
    instante = reportes_cache.guardar(sesion, **clave, contenido=contenido)
    sesion.commit()
    return {**contenido, "instante_calculo": instante.isoformat()}
