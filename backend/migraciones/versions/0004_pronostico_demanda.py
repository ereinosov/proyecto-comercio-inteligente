"""Pronóstico de demanda: demanda_observada, demanda_corregida, pronostico,
sustitucion_producto (data-model.md de 004-pronostico-demanda, constitución v2.2.4).

`demanda_observada`/`demanda_corregida` se materializan por upsert sobre la ventana de días
solicitada al leer (recompute-on-read, research.md #3) — nunca por disparador ni tarea de fondo.
`demanda_observada` es un registro de hechos: no se modifica retroactivamente (FR-004). Las
columnas `es_sintetico`/`demanda_latente_verdadera` sostienen la validación de la User Story 2
(datos sintéticos con demanda latente conocida) sin duplicar el esquema — toda consulta de
producción filtra `es_sintetico = FALSE` (FR-017). `pronostico` es append-only (Principio IV).
`sustitucion_producto` es la relación declarada manualmente entre dos productos (FR-032, User
Story 6, FR-009 b) — añadida a la tabla de propiedad de la constitución por la enmienda v2.2.4,
mismo patrón que `rol_producto` de 003 (tabla propia, FK a `producto`, sin tocar su esquema).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RESPALDO_QUIEBRE = "respaldo_quiebre IN ('no_aplica','metodo_base','consulta_no_atendida')"
_HORIZONTE = "horizonte IN ('corto','medio')"


def upgrade() -> None:
    op.create_table(
        "demanda_observada",
        sa.Column(
            "id_producto",
            sa.Integer(),
            sa.ForeignKey("producto.id_producto"),
            primary_key=True,
        ),
        sa.Column(
            "id_sucursal",
            sa.Integer(),
            sa.ForeignKey("sucursal.id_sucursal"),
            primary_key=True,
        ),
        sa.Column("periodo", sa.Date(), primary_key=True),
        sa.Column("cantidad", sa.Numeric(14, 0), nullable=False),
        sa.Column(
            "dias_en_quiebre",
            sa.Numeric(4, 3),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("precio_vigente_periodo", sa.Numeric(12, 4), nullable=True),
        sa.Column("con_promocion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("es_sintetico", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("demanda_latente_verdadera", sa.Numeric(14, 4), nullable=True),
        sa.Column("consultas_no_atendidas_sinteticas", sa.Integer(), nullable=True),
        sa.Column("instante_materializacion", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_demanda_observada_sucursal_periodo",
        "demanda_observada",
        ["id_sucursal", "periodo"],
    )

    op.create_table(
        "demanda_corregida",
        sa.Column(
            "id_producto",
            sa.Integer(),
            sa.ForeignKey("producto.id_producto"),
            primary_key=True,
        ),
        sa.Column(
            "id_sucursal",
            sa.Integer(),
            sa.ForeignKey("sucursal.id_sucursal"),
            primary_key=True,
        ),
        sa.Column("periodo", sa.Date(), primary_key=True),
        sa.Column("valor_observado", sa.Numeric(14, 0), nullable=False),
        sa.Column("valor", sa.Numeric(14, 4), nullable=False),
        sa.Column(
            "correccion_quiebre",
            sa.Numeric(14, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "respaldo_quiebre",
            sa.String(),
            nullable=False,
            server_default="no_aplica",
        ),
        sa.Column(
            "ajuste_cruzado_sustituto",
            sa.Numeric(14, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "correccion_precio",
            sa.Numeric(14, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("elasticidad_usada", sa.Numeric(4, 3), nullable=True),
        sa.Column(
            "excluido_por_promocion",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("censura_total", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("es_sintetico", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("instante_materializacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_RESPALDO_QUIEBRE, name="ck_demanda_corregida_respaldo_quiebre"),
    )
    op.create_index(
        "ix_demanda_corregida_sucursal_periodo",
        "demanda_corregida",
        ["id_sucursal", "periodo"],
    )

    op.create_table(
        "pronostico",
        sa.Column("id_pronostico", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_producto",
            sa.Integer(),
            sa.ForeignKey("producto.id_producto"),
            nullable=False,
        ),
        sa.Column(
            "id_sucursal",
            sa.Integer(),
            sa.ForeignKey("sucursal.id_sucursal"),
            nullable=False,
        ),
        sa.Column("horizonte", sa.String(), nullable=False),
        sa.Column("dias_horizonte", sa.SmallInteger(), nullable=False),
        sa.Column("serie_pronosticada", JSONB(), nullable=False),
        sa.Column("nivel_suavizado", sa.Numeric(14, 4), nullable=False),
        sa.Column("alfa_usado", sa.Numeric(4, 3), nullable=False),
        sa.Column("multiplicadores_tramo", JSONB(), nullable=True),
        sa.Column("periodo_datos_desde", sa.Date(), nullable=False),
        sa.Column("periodo_datos_hasta", sa.Date(), nullable=False),
        sa.Column("valor_linea_base", sa.Numeric(14, 4), nullable=False),
        sa.Column("error_retrospectivo", sa.Numeric(14, 4), nullable=True),
        sa.Column("error_linea_base", sa.Numeric(14, 4), nullable=True),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("motivo_no_vigente", sa.String(), nullable=True),
        sa.Column("es_sintetico", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("instante_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_HORIZONTE, name="ck_pronostico_horizonte"),
    )
    op.create_index(
        "ix_pronostico_producto_sucursal_horizonte",
        "pronostico",
        ["id_producto", "id_sucursal", "horizonte", "instante_generacion"],
    )

    op.create_table(
        "sustitucion_producto",
        sa.Column("id_sustitucion_producto", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_producto",
            sa.Integer(),
            sa.ForeignKey("producto.id_producto"),
            nullable=False,
        ),
        sa.Column(
            "id_producto_sustituto",
            sa.Integer(),
            sa.ForeignKey("producto.id_producto"),
            nullable=False,
        ),
        sa.Column("instante_declaracion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "id_producto <> id_producto_sustituto",
            name="ck_sustitucion_producto_distinto",
        ),
        sa.UniqueConstraint(
            "id_producto",
            "id_producto_sustituto",
            name="uq_sustitucion_producto_dirigida",
        ),
    )
    op.create_index("ix_sustitucion_producto_id_producto", "sustitucion_producto", ["id_producto"])
    op.create_index(
        "ix_sustitucion_producto_sustituto",
        "sustitucion_producto",
        ["id_producto_sustituto"],
    )


def downgrade() -> None:
    op.drop_index("ix_sustitucion_producto_sustituto", table_name="sustitucion_producto")
    op.drop_index("ix_sustitucion_producto_id_producto", table_name="sustitucion_producto")
    op.drop_table("sustitucion_producto")
    op.drop_index("ix_pronostico_producto_sucursal_horizonte", table_name="pronostico")
    op.drop_table("pronostico")
    op.drop_index("ix_demanda_corregida_sucursal_periodo", table_name="demanda_corregida")
    op.drop_table("demanda_corregida")
    op.drop_index("ix_demanda_observada_sucursal_periodo", table_name="demanda_observada")
    op.drop_table("demanda_observada")
