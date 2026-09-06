"""Caja, mermas y fraude: arqueo, merma, anomalia_caja (data-model.md de 006-caja-mermas-fraude,
constitución v2.2.5).

Tres fenómenos con lógica de detección distinta (FR-037), cada uno con su registro:
- `arqueo` — cuadre de efectivo por cierre de turno (fenómeno 2). NUEVA: 001 tiene conteo físico de
  inventario (`conteo_fisico`) pero ninguna noción de arqueo de efectivo.
- `merma` — pérdida física sin venta asociada, clasificada por causa y valorada al costo del lote
  FEFO de 001 (fenómeno 1). FK `id_conteo_renglon` -> `conteo_renglon` de 001: la tabla destino
  existe en el esquema `0001` aunque su servicio no esté implementado (research.md #10).
- `anomalia_caja` — diferencia (de efectivo o de inventario) que ninguna causa conocida explica
  (fenómeno 3 + residuo). Se calcula consultando `movimiento_inventario`/`venta`/`anulacion_venta`
  de 001 (legítimo por la constitución). El sistema NUNCA fuerza una clasificación ni la cierra por
  el paso del tiempo (FR-029).

Los indicadores por operador (tasa de anulaciones, concentración de ventas bajo precio de lista,
cruce inventario-ventas) NO son entidad: cálculo derivado sobre 001 (research.md #2, #7). El único
valor de indicador que se persiste es `anomalia_caja.indicador_snapshot` (JSONB).

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CAUSA_MERMA = (
    "causa IN ('vencimiento','dano','robo_externo','error_conteo','merma_granel',"
    "'pendiente_clasificar')"
)
_ESTADO_MERMA = "estado IN ('pendiente_clasificar','clasificada')"
_ORIGEN_ANOMALIA = "origen IN ('efectivo','inventario')"
_ESTADO_ANOMALIA = "estado IN ('sin_explicacion','resuelta')"
# La resolución (quién y cuándo) existe si y sólo si la anomalía está resuelta (FR-030).
_RESOLUCION_COHERENTE = (
    "(id_operador_resolucion IS NOT NULL) = (estado = 'resuelta')"
    " AND (instante_resolucion IS NOT NULL) = (estado = 'resuelta')"
)


def upgrade() -> None:
    op.create_table(
        "arqueo",
        sa.Column("id_arqueo", sa.BigInteger(), primary_key=True),
        # Idempotencia de FR-005: un turno se arquea a lo sumo una vez.
        sa.Column(
            "id_turno",
            sa.Integer(),
            sa.ForeignKey("turno.id_turno"),
            nullable=False,
            unique=True,
        ),
        # Denormalizados de `turno` (inmutables): el turno no cambia de operador, sucursal ni
        # instante de cierre (research.md #4).
        sa.Column(
            "id_operador", sa.Integer(), sa.ForeignKey("operador.id_operador"), nullable=False
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column("dia_local", sa.Date(), nullable=False),
        sa.Column("monto_esperado", sa.Numeric(12, 2), nullable=False),
        sa.Column("monto_contado", sa.Numeric(12, 2), nullable=False),
        sa.Column("diferencia", sa.Numeric(12, 2), nullable=False),
        sa.Column("motivo_conocido", sa.Text(), nullable=True),
        sa.Column("ajustes", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("instante_cierre_arqueo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("marca_tiempo_origen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
    )
    op.create_index("ix_arqueo_sucursal_dia_local", "arqueo", ["id_sucursal", "dia_local"])

    op.create_table(
        "merma",
        sa.Column("id_merma", sa.BigInteger(), primary_key=True),
        # La tabla `conteo_renglon` existe en el esquema `0001`; su servicio (001 User Story 5,
        # T065-T071) no. La rama de `clasificar_merma` que usa esta FK está bloqueada (research.md
        # #10); el esquema se crea completo.
        sa.Column(
            "id_conteo_renglon",
            sa.BigInteger(),
            sa.ForeignKey("conteo_renglon.id_conteo_renglon"),
            nullable=True,
        ),
        sa.Column(
            "id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False
        ),
        sa.Column("id_lote", sa.Integer(), sa.ForeignKey("lote.id_lote"), nullable=True),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        # Escala idéntica a `conteo_renglon.diferencia` y `movimiento_inventario.cantidad` de 001:
        # entero, gramos para granel (data-model.md).
        sa.Column("cantidad_faltante", sa.Numeric(14, 0), nullable=False),
        sa.Column("causa", sa.String(), nullable=False),
        # NULL = "no calculable" (falta el costo del lote). NUNCA 0.00 (FR-010).
        sa.Column("valoracion", sa.Numeric(12, 2), nullable=True),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column(
            "estado", sa.String(), nullable=False, server_default="pendiente_clasificar"
        ),
        sa.Column(
            "conciliar_con_conteo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        # Quién registró/clasificó — NO es una imputación de la pérdida a ese operador (FR-011).
        sa.Column(
            "id_operador_registro",
            sa.Integer(),
            sa.ForeignKey("operador.id_operador"),
            nullable=False,
        ),
        sa.Column("instante_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.CheckConstraint(_CAUSA_MERMA, name="ck_merma_causa"),
        sa.CheckConstraint(_ESTADO_MERMA, name="ck_merma_estado"),
        sa.CheckConstraint("cantidad_faltante > 0", name="ck_merma_cantidad_positiva"),
        sa.CheckConstraint("periodo_hasta >= periodo_desde", name="ck_merma_periodo"),
        sa.CheckConstraint(
            "valoracion IS NULL OR valoracion >= 0", name="ck_merma_valoracion_no_negativa"
        ),
    )
    op.create_index("ix_merma_sucursal_periodo", "merma", ["id_sucursal", "periodo_hasta"])
    op.create_index("ix_merma_producto_periodo", "merma", ["id_producto", "periodo_hasta"])
    # Una línea de conteo se clasifica a lo sumo una vez.
    op.create_index(
        "uq_merma_conteo_renglon",
        "merma",
        ["id_conteo_renglon"],
        unique=True,
        postgresql_where=sa.text("id_conteo_renglon IS NOT NULL"),
    )

    op.create_table(
        "anomalia_caja",
        sa.Column("id_anomalia_caja", sa.BigInteger(), primary_key=True),
        sa.Column("origen", sa.String(), nullable=False),
        sa.Column(
            "estado", sa.String(), nullable=False, server_default="sin_explicacion"
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column(
            "id_arqueo", sa.BigInteger(), sa.ForeignKey("arqueo.id_arqueo"), nullable=True
        ),
        sa.Column("id_turno", sa.Integer(), sa.ForeignKey("turno.id_turno"), nullable=True),
        sa.Column(
            "id_operador", sa.Integer(), sa.ForeignKey("operador.id_operador"), nullable=True
        ),
        sa.Column(
            "id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=True
        ),
        # FK de sólo lectura a `conteo_fisico` de 001 — tabla presente en el esquema `0001`.
        sa.Column(
            "id_conteo_fisico",
            sa.Integer(),
            sa.ForeignKey("conteo_fisico.id_conteo_fisico"),
            nullable=True,
        ),
        sa.Column("monto", sa.Numeric(12, 2), nullable=True),
        sa.Column("magnitud", sa.Numeric(14, 0), nullable=True),
        sa.Column("valor_estimado", sa.Numeric(12, 2), nullable=True),
        sa.Column("periodo_desde", sa.Date(), nullable=True),
        sa.Column("periodo_hasta", sa.Date(), nullable=True),
        sa.Column("dia_local", sa.Date(), nullable=False),
        # Indicadores por operador CONGELADOS en el momento de generarse (origen inventario), para
        # que no cambien si después se anula una venta del cálculo (research.md #2, #6).
        sa.Column("indicador_snapshot", JSONB(), nullable=True),
        # Historial de cambios de estado (FR-030): columna en la fila, NO tabla hija (research.md #6).
        sa.Column(
            "historial", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        # Texto libre, NO un ENUM cerrado (FR-029 prohíbe imponer una clasificación; research.md #18).
        sa.Column("resolucion", sa.Text(), nullable=True),
        sa.Column(
            "id_operador_resolucion",
            sa.Integer(),
            sa.ForeignKey("operador.id_operador"),
            nullable=True,
        ),
        sa.Column("instante_resolucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("instante_deteccion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
        sa.CheckConstraint(_ORIGEN_ANOMALIA, name="ck_anomalia_caja_origen"),
        sa.CheckConstraint(_ESTADO_ANOMALIA, name="ck_anomalia_caja_estado"),
        sa.CheckConstraint(_RESOLUCION_COHERENTE, name="ck_anomalia_caja_resolucion_coherente"),
    )
    op.create_index(
        "ix_anomalia_caja_sucursal_estado", "anomalia_caja", ["id_sucursal", "estado"]
    )
    op.create_index("ix_anomalia_caja_origen_estado", "anomalia_caja", ["origen", "estado"])
    op.create_index(
        "uq_anomalia_caja_arqueo",
        "anomalia_caja",
        ["id_arqueo"],
        unique=True,
        postgresql_where=sa.text("id_arqueo IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_anomalia_caja_arqueo", table_name="anomalia_caja")
    op.drop_index("ix_anomalia_caja_origen_estado", table_name="anomalia_caja")
    op.drop_index("ix_anomalia_caja_sucursal_estado", table_name="anomalia_caja")
    op.drop_table("anomalia_caja")
    op.drop_index("uq_merma_conteo_renglon", table_name="merma")
    op.drop_index("ix_merma_producto_periodo", table_name="merma")
    op.drop_index("ix_merma_sucursal_periodo", table_name="merma")
    op.drop_table("merma")
    op.drop_index("ix_arqueo_sucursal_dia_local", table_name="arqueo")
    op.drop_table("arqueo")
