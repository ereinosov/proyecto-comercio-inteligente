"""Reportes e inteligencia: agregado_reporte, segmento_cliente, asignacion_segmento
(data-model.md de 008-reportes-inteligencia, constitución v2.6.0).

Las TRES entidades son DERIVADAS y regenerables — caché y resultado de cálculo sobre 001–006,
nunca fuente de verdad de negocio. `downgrade` las elimina sin pérdida de dato de negocio.

- `agregado_reporte` — caché de una vista (comparativo / tendencia / tablero) por (tipo, ámbito
  de sucursal, período, granularidad). `UNIQUE` sobre esa clave; "Actualizar" hace DELETE +
  recálculo.
- `segmento_cliente` — definición de cada grupo del último clustering (centroide por eje,
  descripción derivada del centroide, semilla). `UNIQUE (corrida, etiqueta_grupo)`.
- `asignacion_segmento` — cliente ↔ grupo del mismo recálculo. `ON DELETE CASCADE` desde
  `cliente`: 008 no retiene un cliente que 002 ya anonimizó/borró.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agregado_reporte",
        sa.Column("id_agregado_reporte", sa.BigInteger(), primary_key=True),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column(
            "ambito_sucursal",
            sa.Integer(),
            sa.ForeignKey("sucursal.id_sucursal"),
            nullable=True,
        ),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fin", sa.Date(), nullable=False),
        sa.Column("granularidad", sa.Text(), nullable=False),
        sa.Column("contenido", JSONB(), nullable=False),
        sa.Column("instante_calculo", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('comparativo','tendencia','tablero')", name="ck_agregado_reporte_tipo"
        ),
        sa.CheckConstraint(
            "granularidad IN ('total','semana','mes')", name="ck_agregado_reporte_gran"
        ),
        sa.UniqueConstraint(
            "tipo",
            "ambito_sucursal",
            "periodo_inicio",
            "periodo_fin",
            "granularidad",
            name="uq_agregado_reporte_clave",
        ),
    )

    op.create_table(
        "segmento_cliente",
        sa.Column("id_segmento_cliente", sa.BigInteger(), primary_key=True),
        sa.Column("corrida", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etiqueta_grupo", sa.Text(), nullable=False),
        sa.Column("centroide_frecuencia", sa.Numeric(10, 4), nullable=False),
        sa.Column("centroide_margen", sa.Numeric(6, 4), nullable=False),
        sa.Column("centroide_recencia_dias", sa.Numeric(8, 2), nullable=False),
        sa.Column("n_clientes", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("semilla", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint(
            "corrida", "etiqueta_grupo", name="uq_segmento_cliente_corrida_grupo"
        ),
    )

    op.create_table(
        "asignacion_segmento",
        sa.Column(
            "id_cliente",
            sa.Integer(),
            sa.ForeignKey("cliente.id_cliente", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("corrida", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etiqueta_grupo", sa.Text(), nullable=False),
        sa.Column("distancia_al_centroide", sa.Numeric(10, 4), nullable=True),
        sa.ForeignKeyConstraint(
            ["corrida", "etiqueta_grupo"],
            ["segmento_cliente.corrida", "segmento_cliente.etiqueta_grupo"],
            name="fk_asignacion_segmento_grupo",
        ),
    )


def downgrade() -> None:
    op.drop_table("asignacion_segmento")
    op.drop_table("segmento_cliente")
    op.drop_table("agregado_reporte")
