"""Clientes y fidelización: cliente, visita, intervalo_compra, senal_fuga (data-model.md).

`visita.margen_relativo` es un ratio (research.md #2 de 002), no un monto: nunca escalarlo como
un importe. `cliente.nombre`/`fecha_nacimiento`/`contacto` son NULL-ables únicamente para admitir
el estado post-anonimización (FR-016 de 002); la API exige los dos primeros al registrar (FR-001).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cliente",
        sa.Column("id_cliente", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=True),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("contacto", sa.String(), nullable=True),
        sa.Column("fecha_alta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("anonimizado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("instante_anonimizacion", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "visita",
        sa.Column("id_visita", sa.BigInteger(), primary_key=True),
        sa.Column("id_cliente", sa.Integer(), sa.ForeignKey("cliente.id_cliente"), nullable=False),
        sa.Column(
            "id_venta", sa.BigInteger(), sa.ForeignKey("venta.id_venta"), nullable=False, unique=True
        ),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.Column("monto_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("margen_relativo", sa.Numeric(6, 4), nullable=False),
    )
    op.create_index("ix_visita_cliente", "visita", ["id_cliente"])

    op.create_table(
        "intervalo_compra",
        sa.Column(
            "id_cliente", sa.Integer(), sa.ForeignKey("cliente.id_cliente"), primary_key=True
        ),
        sa.Column("intervalo_esperado_dias", sa.Numeric(8, 2), nullable=True),
        sa.Column("visitas_consideradas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(), nullable=False, server_default="datos_insuficientes"),
        sa.Column("instante_calculo", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "estado IN ('datos_insuficientes','calculado')", name="ck_intervalo_compra_estado"
        ),
    )

    op.create_table(
        "senal_fuga",
        sa.Column("id_senal_fuga", sa.BigInteger(), primary_key=True),
        sa.Column("id_cliente", sa.Integer(), sa.ForeignKey("cliente.id_cliente"), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("instante_deteccion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instante_confirmacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("instante_resolucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("instante_purga_programada", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('activa','confirmada','resuelta')", name="ck_senal_fuga_estado"
        ),
    )
    # Índice único parcial: a lo sumo una señal abierta (activa o confirmada) por cliente a la
    # vez (data-model.md). Una señal `resuelta` no cuenta: permite una fila nueva ante reincidencia.
    op.execute(
        "CREATE UNIQUE INDEX uq_senal_fuga_abierta ON senal_fuga (id_cliente) "
        "WHERE estado IN ('activa', 'confirmada')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_senal_fuga_abierta")
    op.drop_table("senal_fuga")
    op.drop_table("intervalo_compra")
    op.drop_index("ix_visita_cliente", table_name="visita")
    op.drop_table("visita")
    op.drop_table("cliente")
