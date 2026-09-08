"""Segmentación de clientes por similitud (008-reportes-inteligencia, User Story 4).

k-means propio (`dominio/kmeans`) sobre tres ejes normalizados —frecuencia, margen, recencia—
derivados de datos que 002 ya calcula (`visita`, `intervalo_compra`). Solo lectura sobre 002;
escribe únicamente en `segmento_cliente` / `asignacion_segmento` de 008.

Determinista (FR-019): semilla fija `SEMILLA_SEGMENTOS`, clientes recorridos en orden de
`id_cliente`. Recálculo POR LOTE disparado por una persona (FR-020). Clientes con < N visitas →
grupo `sin_clasificar` (FR-021). Sin ningún cliente clasificable → 409 (FR-024).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from rasero.config.reportes import K_SEGMENTOS, MIN_VISITAS_CLASIFICABLE, SEMILLA_SEGMENTOS
from rasero.dominio.kmeans import agrupar, describir_centroide, estandarizar
from rasero.errores import SinBaseParaSegmentar
from rasero.persistencia.modelos import (
    AsignacionSegmento,
    Cliente,
    IntervaloCompra,
    SegmentoCliente,
    Visita,
)

_SIN_CLASIFICAR = "sin_clasificar"


def extraer_features(sesion: Session) -> list[tuple[int, float, float, float]]:
    """`(id_cliente, frecuencia_por_dia, margen_medio, recencia_dias)` para los clientes NO
    anonimizados con ≥ `MIN_VISITAS_CLASIFICABLE` visitas. Ordenados por `id_cliente`.
    """
    ahora = datetime.now(timezone.utc)
    agg = sesion.execute(
        select(
            Visita.id_cliente,
            func.count(Visita.id_visita),
            func.min(Visita.instante),
            func.max(Visita.instante),
            func.avg(Visita.margen_relativo),
        )
        .join(Cliente, Cliente.id_cliente == Visita.id_cliente)
        .where(Cliente.anonimizado.is_(False))
        .group_by(Visita.id_cliente)
        .having(func.count(Visita.id_visita) >= MIN_VISITAS_CLASIFICABLE)
        .order_by(Visita.id_cliente)
    ).all()

    intervalos = dict(
        sesion.execute(
            select(IntervaloCompra.id_cliente, IntervaloCompra.intervalo_esperado_dias).where(
                IntervaloCompra.estado == "calculado",
                IntervaloCompra.intervalo_esperado_dias.is_not(None),
            )
        ).all()
    )

    filas: list[tuple[int, float, float, float]] = []
    for id_cliente, n, primera, ultima, margen in agg:
        intervalo = intervalos.get(id_cliente)
        if intervalo and Decimal(intervalo) > 0:
            frecuencia = 1.0 / float(intervalo)
        else:
            span = max(1.0, (ultima - primera).total_seconds() / 86400)
            frecuencia = n / span
        recencia = max(0.0, (ahora - ultima).total_seconds() / 86400)
        filas.append((id_cliente, frecuencia, float(margen), recencia))
    return filas


def recalcular(sesion: Session) -> dict:
    features = extraer_features(sesion)
    todos = [
        c
        for (c,) in sesion.execute(
            select(Cliente.id_cliente).where(Cliente.anonimizado.is_(False))
        ).all()
    ]

    if not features:
        raise SinBaseParaSegmentar()

    corrida = datetime.now(timezone.utc)
    ids = [f[0] for f in features]
    # Eje 3 invertido: "más reciente" = más alto, misma dirección que frecuencia y margen.
    puntos = [(f[1], f[2], -f[3]) for f in features]
    z, medias, desv = estandarizar(puntos)
    grupos, centroides_z = agrupar(z, K_SEGMENTOS, SEMILLA_SEGMENTOS)

    # Limpia la corrida anterior.
    sesion.execute(delete(AsignacionSegmento))
    sesion.execute(delete(SegmentoCliente))
    sesion.flush()

    def _orig(cz: tuple[float, float, float]) -> tuple[Decimal, Decimal, Decimal]:
        fr = medias[0] + cz[0] * desv[0]
        mg = medias[1] + cz[1] * desv[1]
        rec_inv = medias[2] + cz[2] * desv[2]
        return (
            Decimal(str(round(fr, 4))),
            Decimal(str(round(mg, 4))),
            Decimal(str(round(-rec_inv, 2))),
        )

    k_real = len(centroides_z)
    conteo = [grupos.count(j) for j in range(k_real)]
    for j in range(k_real):
        fr, mg, rec = _orig(centroides_z[j])
        sesion.add(
            SegmentoCliente(
                corrida=corrida,
                etiqueta_grupo=f"grupo_{j + 1}",
                centroide_frecuencia=fr,
                centroide_margen=mg,
                centroide_recencia_dias=rec,
                n_clientes=conteo[j],
                descripcion=describir_centroide(centroides_z[j]),
                semilla=SEMILLA_SEGMENTOS,
            )
        )

    sin_clasif = [c for c in todos if c not in set(ids)]
    if sin_clasif:
        sesion.add(
            SegmentoCliente(
                corrida=corrida,
                etiqueta_grupo=_SIN_CLASIFICAR,
                centroide_frecuencia=Decimal("0"),
                centroide_margen=Decimal("0"),
                centroide_recencia_dias=Decimal("0"),
                n_clientes=len(sin_clasif),
                descripcion="todavía no tienen suficiente historial (menos de "
                f"{MIN_VISITAS_CLASIFICABLE} visitas) para agruparlos",
                semilla=SEMILLA_SEGMENTOS,
            )
        )
    sesion.flush()

    def _dist2(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    for (id_cliente, _, _, _), pz, g in zip(features, z, grupos):
        sesion.add(
            AsignacionSegmento(
                id_cliente=id_cliente,
                corrida=corrida,
                etiqueta_grupo=f"grupo_{g + 1}",
                distancia_al_centroide=Decimal(str(round(_dist2(pz, centroides_z[g]) ** 0.5, 4))),
            )
        )
    for c in sin_clasif:
        sesion.add(
            AsignacionSegmento(
                id_cliente=c, corrida=corrida, etiqueta_grupo=_SIN_CLASIFICAR,
                distancia_al_centroide=None,
            )
        )

    sesion.commit()
    return leer(sesion)


def _ultima_corrida(sesion: Session) -> datetime | None:
    return sesion.execute(select(func.max(SegmentoCliente.corrida))).scalar_one_or_none()


def leer(sesion: Session) -> dict:
    corrida = _ultima_corrida(sesion)
    if corrida is None:
        return {"calculado": False, "corrida": None, "semilla": None, "grupos": []}

    grupos = sesion.execute(
        select(SegmentoCliente).where(SegmentoCliente.corrida == corrida).order_by(
            SegmentoCliente.etiqueta_grupo
        )
    ).scalars().all()

    salida = []
    for g in grupos:
        ejemplos = sesion.execute(
            select(Cliente.id_cliente, Cliente.nombre)
            .join(AsignacionSegmento, AsignacionSegmento.id_cliente == Cliente.id_cliente)
            .where(
                AsignacionSegmento.corrida == corrida,
                AsignacionSegmento.etiqueta_grupo == g.etiqueta_grupo,
            )
            .order_by(AsignacionSegmento.distancia_al_centroide.nulls_last())
            .limit(3)
        ).all()
        salida.append(
            {
                "etiqueta_grupo": g.etiqueta_grupo,
                "descripcion": g.descripcion,
                "n_clientes": g.n_clientes,
                "centroide": {
                    "frecuencia": f"{g.centroide_frecuencia}",
                    "margen": f"{g.centroide_margen}",
                    "recencia_dias": f"{g.centroide_recencia_dias}",
                },
                "ejemplos": [{"id_cliente": i, "nombre": n} for i, n in ejemplos],
            }
        )

    return {
        "calculado": True,
        "corrida": corrida.isoformat(),
        "semilla": SEMILLA_SEGMENTOS,
        "grupos": salida,
    }


def etiqueta_de_cliente(sesion: Session, *, id_cliente: int) -> dict:
    corrida = _ultima_corrida(sesion)
    if corrida is None:
        return {"id_cliente": id_cliente, "etiqueta_grupo": None, "descripcion": None, "corrida": None}
    fila = sesion.execute(
        select(AsignacionSegmento.etiqueta_grupo, SegmentoCliente.descripcion)
        .join(
            SegmentoCliente,
            (SegmentoCliente.corrida == AsignacionSegmento.corrida)
            & (SegmentoCliente.etiqueta_grupo == AsignacionSegmento.etiqueta_grupo),
        )
        .where(
            AsignacionSegmento.corrida == corrida,
            AsignacionSegmento.id_cliente == id_cliente,
        )
    ).one_or_none()
    if fila is None:
        return {"id_cliente": id_cliente, "etiqueta_grupo": None, "descripcion": None, "corrida": corrida.isoformat()}
    return {
        "id_cliente": id_cliente,
        "etiqueta_grupo": fila[0],
        "descripcion": fila[1],
        "corrida": corrida.isoformat(),
    }
