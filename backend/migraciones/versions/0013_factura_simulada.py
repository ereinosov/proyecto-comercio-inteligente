"""Facturación electrónica SIMULADA: factura_simulada (data-model.md de
009-facturacion-electronica, constitución v2.7.0).

Entidad propia de 009, DERIVADA de una `venta` ya confirmada de 001. 009 CONSULTA
`venta`/`renglon_venta`/`cliente` sin poseerlos y NO altera su esquema. `downgrade` elimina la
tabla sin pérdida de dato de negocio (la factura es reconstruible de la venta).

SIMULADA: sin conexión al SRI, sin firma electrónica, sin XML regulatorio (mismo criterio que
007 para "sin pasarela real").

- `UNIQUE (id_venta) WHERE tipo = 'factura'` — una venta, una factura (idempotencia). Una
  `nota_credito` comparte `id_venta` con la factura que revierte, de ahí el índice PARCIAL.
- `UNIQUE (establecimiento, punto_emision, tipo, numero)` — correlativo sin huecos ni
  repeticiones por punto de emisión.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "factura_simulada",
        sa.Column("id_factura_simulada", sa.BigInteger(), primary_key=True),
        sa.Column("id_venta", sa.BigInteger(), sa.ForeignKey("venta.id_venta"), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column(
            "id_factura_referida",
            sa.BigInteger(),
            sa.ForeignKey("factura_simulada.id_factura_simulada"),
            nullable=True,
        ),
        sa.Column("establecimiento", sa.Text(), nullable=False),
        sa.Column("punto_emision", sa.Text(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("secuencial", sa.Text(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("emisor", JSONB(), nullable=False),
        sa.Column("comprador", JSONB(), nullable=False),
        sa.Column("renglones", JSONB(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tarifa_iva", sa.Numeric(5, 4), nullable=False),
        sa.Column("monto_iva", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("medio_pago", sa.Text(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False, server_default="emitida"),
        sa.Column("instante_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo IN ('factura','nota_credito')", name="ck_factura_simulada_tipo"),
        sa.CheckConstraint(
            "estado IN ('emitida','anulada')", name="ck_factura_simulada_estado"
        ),
        sa.CheckConstraint("numero >= 1", name="ck_factura_simulada_numero"),
        sa.CheckConstraint(
            "(tipo = 'nota_credito') = (id_factura_referida IS NOT NULL)",
            name="ck_factura_simulada_referencia",
        ),
        sa.UniqueConstraint(
            "establecimiento", "punto_emision", "tipo", "numero",
            name="uq_factura_simulada_secuencial",
        ),
    )
    op.create_index(
        "uq_factura_simulada_una_por_venta",
        "factura_simulada",
        ["id_venta"],
        unique=True,
        postgresql_where=sa.text("tipo = 'factura'"),
    )


def downgrade() -> None:
    op.drop_index("uq_factura_simulada_una_por_venta", table_name="factura_simulada")
    op.drop_table("factura_simulada")
