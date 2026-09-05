"""Precios y márgenes: rol_producto, margen_calculado, sugerencia_precio,
sugerencia_colocacion (data-model.md de 003-precios-margenes).

`margen_calculado` se recalcula y sobrescribe (upsert) en cada lectura, nunca por disparador ni
tarea de fondo (research.md #4 de 003): `costo_vigente`/`margen` son NULL-ables porque un producto
sin existencia con lote no tiene margen calculable (FR-003), no cero. `sugerencia_precio` y
`sugerencia_colocacion` son append-only (Principio IV): cada sugerencia generada es una fila nueva,
con los insumos (`margen_usado`, `rol_usado`, observación de competencia usada) congelados como
snapshot en el instante de generación, no como referencia mutable (ver data-model.md).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rol_producto",
        sa.Column(
            "id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), primary_key=True
        ),
        sa.Column("rol", sa.String(), nullable=False),
        sa.Column("instante_asignacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rol IN ('gancho_trafico','generador_margen')", name="ck_rol_producto_rol"
        ),
    )

    op.create_table(
        "margen_calculado",
        sa.Column(
            "id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), primary_key=True
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), primary_key=True
        ),
        sa.Column("costo_vigente", sa.Numeric(12, 4), nullable=True),
        sa.Column("precio_vigente", sa.Numeric(12, 4), nullable=False),
        sa.Column("margen", sa.Numeric(6, 4), nullable=True),
        sa.Column("confiable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("instante_calculo", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "sugerencia_precio",
        sa.Column("id_sugerencia_precio", sa.BigInteger(), primary_key=True),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("precio_sugerido", sa.Numeric(12, 4), nullable=False),
        sa.Column("margen_usado", sa.Numeric(6, 4), nullable=True),
        sa.Column("rol_usado", sa.String(), nullable=True),
        sa.Column(
            "id_observacion_precio_usada",
            sa.BigInteger(),
            sa.ForeignKey("observacion_precio.id_observacion_precio"),
            nullable=True,
        ),
        sa.Column("instante_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aplicada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("instante_aplicacion", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "rol_usado IS NULL OR rol_usado IN ('gancho_trafico','generador_margen')",
            name="ck_sugerencia_precio_rol_usado",
        ),
    )
    op.create_index(
        "ix_sugerencia_precio_producto_sucursal",
        "sugerencia_precio",
        ["id_producto", "id_sucursal"],
    )

    op.create_table(
        "sugerencia_colocacion",
        sa.Column("id_sugerencia_colocacion", sa.BigInteger(), primary_key=True),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column(
            "id_zona_exhibicion",
            sa.Integer(),
            sa.ForeignKey("zona_exhibicion.id_zona_exhibicion"),
            nullable=False,
        ),
        sa.Column("margen_usado", sa.Numeric(6, 4), nullable=True),
        sa.Column("rol_usado", sa.String(), nullable=True),
        sa.Column("instante_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aplicada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("instante_aplicacion", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "rol_usado IS NULL OR rol_usado IN ('gancho_trafico','generador_margen')",
            name="ck_sugerencia_colocacion_rol_usado",
        ),
    )
    op.create_index(
        "ix_sugerencia_colocacion_producto_sucursal",
        "sugerencia_colocacion",
        ["id_producto", "id_sucursal"],
    )


def downgrade() -> None:
    op.drop_index("ix_sugerencia_colocacion_producto_sucursal", table_name="sugerencia_colocacion")
    op.drop_table("sugerencia_colocacion")
    op.drop_index("ix_sugerencia_precio_producto_sucursal", table_name="sugerencia_precio")
    op.drop_table("sugerencia_precio")
    op.drop_table("margen_calculado")
    op.drop_table("rol_producto")
