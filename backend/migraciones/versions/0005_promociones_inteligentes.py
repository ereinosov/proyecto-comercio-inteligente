"""Promociones inteligentes: campania, cupon, oferta_recompra, experimento_reactivacion,
asignacion_experimento, redencion_promocion (data-model.md de 005-promociones-inteligentes,
constitución v2.2.5).

Tres mecanismos de promoción distintos (Lectura Crítica n.º 6), una entidad por mecanismo en la
**generación** (`cupon`, `oferta_recompra`, `experimento_reactivacion` + `asignacion_experimento`)
y una entidad transversal para el hecho de que uno se usó en una venta (`redencion_promocion`).
`campania` es el paraguas de una corrida de un mecanismo. Nada de esto se recomputa al leer
(a diferencia de `margen_calculado` de 003 o `demanda_corregida` de 004): son hechos con máquina
de estados (research.md #12).

La reserva del empuje por recompra es **de precio, no de inventario**: no hay ninguna columna de
"stock apartado" y `005` nunca escribe contra `existencia`/`movimiento_inventario` de 001 (FR-010,
FR-011). `redencion_promocion` referencia `venta` de 001 por FK de sólo lectura (mismo patrón que
`visita.id_venta` de 002) y denormaliza `id_sucursal`/`periodo` —valores inmutables— para la
consulta de "marca de promoción activa" que 004 consume (research.md #4).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TIPO_CAMPANIA = "tipo IN ('fecha_fija','recompra','reactivacion')"
_MOTIVO_CUPON = "motivo IN ('fecha_fija_cumpleanos')"
_ESTADO_CUPON = "estado IN ('generado','redimido','vencido')"
_ESTADO_RESERVA = "estado_reserva IN ('vigente','vencida')"
_DESENLACE_OFERTA = "desenlace IN ('pendiente','comprado','no_comprado','reserva_vencida')"
_GRUPO = "grupo IN ('tratamiento','control')"
_VEREDICTO = "veredicto IN ('en_curso','efectivo','no_efectivo','muestra_insuficiente')"
_TIPO_ORIGEN = "tipo_origen IN ('cupon','oferta_recompra','reactivacion')"
# Exactamente un id_* de origen no nulo, coherente con tipo_origen.
_ORIGEN_UNICO = (
    "( (id_cupon IS NOT NULL)::int"
    " + (id_oferta_recompra IS NOT NULL)::int"
    " + (id_asignacion_experimento IS NOT NULL)::int ) = 1"
    " AND (tipo_origen = 'cupon') = (id_cupon IS NOT NULL)"
    " AND (tipo_origen = 'oferta_recompra') = (id_oferta_recompra IS NOT NULL)"
    " AND (tipo_origen = 'reactivacion') = (id_asignacion_experimento IS NOT NULL)"
)


def upgrade() -> None:
    op.create_table(
        "campania",
        sa.Column("id_campania", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=True
        ),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("ventana_desde", sa.Date(), nullable=False),
        sa.Column("ventana_hasta", sa.Date(), nullable=False),
        sa.Column("instante_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_TIPO_CAMPANIA, name="ck_campania_tipo"),
        sa.CheckConstraint("ventana_hasta >= ventana_desde", name="ck_campania_ventana"),
    )
    op.create_index("ix_campania_tipo", "campania", ["tipo"])

    op.create_table(
        "cupon",
        sa.Column("id_cupon", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_campania", sa.Integer(), sa.ForeignKey("campania.id_campania"), nullable=False
        ),
        sa.Column("id_cliente", sa.Integer(), sa.ForeignKey("cliente.id_cliente"), nullable=False),
        sa.Column(
            "motivo",
            sa.String(),
            nullable=False,
            server_default="fecha_fija_cumpleanos",
        ),
        sa.Column("fecha_objetivo", sa.Date(), nullable=False),
        sa.Column("valido_desde", sa.Date(), nullable=False),
        sa.Column("valido_hasta", sa.Date(), nullable=False),
        sa.Column("porcentaje_descuento", sa.Numeric(5, 2), nullable=False),
        sa.Column("estado", sa.String(), nullable=False, server_default="generado"),
        sa.Column("instante_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_MOTIVO_CUPON, name="ck_cupon_motivo"),
        sa.CheckConstraint(_ESTADO_CUPON, name="ck_cupon_estado"),
        sa.UniqueConstraint("id_cliente", "fecha_objetivo", name="uq_cupon_cliente_fecha_objetivo"),
    )
    op.create_index("ix_cupon_estado_valido_hasta", "cupon", ["estado", "valido_hasta"])
    op.create_index("ix_cupon_id_cliente", "cupon", ["id_cliente"])

    op.create_table(
        "oferta_recompra",
        sa.Column("id_oferta_recompra", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_campania", sa.Integer(), sa.ForeignKey("campania.id_campania"), nullable=False
        ),
        sa.Column("id_cliente", sa.Integer(), sa.ForeignKey("cliente.id_cliente"), nullable=False),
        sa.Column(
            "id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column("intervalo_esperado_dias_disparo", sa.Numeric(8, 2), nullable=False),
        sa.Column("justificacion", JSONB(), nullable=False),
        sa.Column("precio_garantizado", sa.Numeric(12, 4), nullable=False),
        sa.Column("reserva_desde", sa.Date(), nullable=False),
        sa.Column("reserva_hasta", sa.Date(), nullable=False),
        sa.Column("estado_reserva", sa.String(), nullable=False, server_default="vigente"),
        sa.Column("desenlace", sa.String(), nullable=False, server_default="pendiente"),
        sa.Column("instante_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_ESTADO_RESERVA, name="ck_oferta_recompra_estado_reserva"),
        sa.CheckConstraint(_DESENLACE_OFERTA, name="ck_oferta_recompra_desenlace"),
    )
    op.create_index(
        "uq_oferta_recompra_activa",
        "oferta_recompra",
        ["id_cliente", "id_producto"],
        unique=True,
        postgresql_where=sa.text("desenlace = 'pendiente'"),
    )
    op.create_index(
        "ix_oferta_recompra_estado_reserva_hasta",
        "oferta_recompra",
        ["estado_reserva", "reserva_hasta"],
    )
    op.create_index("ix_oferta_recompra_id_cliente", "oferta_recompra", ["id_cliente"])

    op.create_table(
        "experimento_reactivacion",
        sa.Column("id_experimento_reactivacion", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_campania", sa.Integer(), sa.ForeignKey("campania.id_campania"), nullable=False
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=True
        ),
        sa.Column("semilla", sa.BigInteger(), nullable=False),
        sa.Column("algoritmo", sa.Text(), nullable=False),
        sa.Column("proporcion_tratamiento", sa.Numeric(4, 3), nullable=False),
        sa.Column("ventana_medicion_dias", sa.SmallInteger(), nullable=False),
        sa.Column("porcentaje_descuento", sa.Numeric(5, 2), nullable=False),
        sa.Column("tasa_retorno_base_esperada", sa.Numeric(5, 4), nullable=False),
        sa.Column("mde_puntos_porcentuales", sa.Numeric(5, 2), nullable=False),
        sa.Column("alfa", sa.Numeric(4, 3), nullable=False),
        sa.Column("poder", sa.Numeric(4, 3), nullable=False),
        sa.Column("tamano_minimo_muestra", sa.Integer(), nullable=False),
        sa.Column("n_elegibles", sa.Integer(), nullable=False),
        sa.Column("n_tratamiento", sa.Integer(), nullable=True),
        sa.Column("n_control", sa.Integer(), nullable=True),
        sa.Column("retorno_tratamiento", sa.Numeric(6, 4), nullable=True),
        sa.Column("retorno_control", sa.Numeric(6, 4), nullable=True),
        sa.Column("incrementalidad", sa.Numeric(6, 4), nullable=True),
        sa.Column("estadistico_z", sa.Numeric(8, 5), nullable=True),
        sa.Column("valor_p", sa.Numeric(7, 6), nullable=True),
        sa.Column("veredicto", sa.String(), nullable=False, server_default="en_curso"),
        sa.Column("instante_asignacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instante_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(_VEREDICTO, name="ck_experimento_reactivacion_veredicto"),
    )
    op.create_index(
        "ix_experimento_reactivacion_id_campania",
        "experimento_reactivacion",
        ["id_campania"],
    )
    op.create_index(
        "ix_experimento_reactivacion_veredicto",
        "experimento_reactivacion",
        ["veredicto"],
    )

    op.create_table(
        "asignacion_experimento",
        sa.Column("id_asignacion_experimento", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_experimento_reactivacion",
            sa.BigInteger(),
            sa.ForeignKey("experimento_reactivacion.id_experimento_reactivacion"),
            nullable=False,
        ),
        sa.Column("id_cliente", sa.Integer(), sa.ForeignKey("cliente.id_cliente"), nullable=False),
        # Referencia de auditoría a `senal_fuga` de 002 (data-model.md): sin FK con cascada — cruza
        # el límite de propiedad; `005` nunca modifica `senal_fuga` (FR-028).
        sa.Column("id_senal_fuga", sa.BigInteger(), nullable=False),
        sa.Column("grupo", sa.String(), nullable=False),
        sa.Column("retorno", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("id_venta_retorno", sa.BigInteger(), nullable=True),
        sa.Column("instante_retorno", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(_GRUPO, name="ck_asignacion_experimento_grupo"),
        sa.UniqueConstraint(
            "id_experimento_reactivacion",
            "id_cliente",
            name="uq_asignacion_experimento_cliente",
        ),
    )
    op.create_index(
        "ix_asignacion_experimento_id_cliente",
        "asignacion_experimento",
        ["id_cliente"],
    )

    op.create_table(
        "redencion_promocion",
        sa.Column("id_redencion_promocion", sa.BigInteger(), primary_key=True),
        sa.Column("tipo_origen", sa.String(), nullable=False),
        sa.Column("id_cupon", sa.BigInteger(), sa.ForeignKey("cupon.id_cupon"), nullable=True),
        sa.Column(
            "id_oferta_recompra",
            sa.BigInteger(),
            sa.ForeignKey("oferta_recompra.id_oferta_recompra"),
            nullable=True,
        ),
        sa.Column(
            "id_asignacion_experimento",
            sa.BigInteger(),
            sa.ForeignKey("asignacion_experimento.id_asignacion_experimento"),
            nullable=True,
        ),
        # FK de sólo lectura a `venta` de 001, sin cascada — mismo patrón que `visita.id_venta`.
        sa.Column("id_venta", sa.BigInteger(), sa.ForeignKey("venta.id_venta"), nullable=False),
        sa.Column(
            "id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=True
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column("periodo", sa.Date(), nullable=False),
        sa.Column("descuento_aplicado", sa.Numeric(12, 4), nullable=True),
        sa.Column("instante_redencion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_TIPO_ORIGEN, name="ck_redencion_promocion_tipo_origen"),
        sa.CheckConstraint(_ORIGEN_UNICO, name="ck_redencion_promocion_origen_unico"),
    )
    op.create_index(
        "ix_redencion_promocion_sucursal_periodo",
        "redencion_promocion",
        ["id_sucursal", "periodo"],
    )
    op.create_index("ix_redencion_promocion_id_venta", "redencion_promocion", ["id_venta"])
    op.create_index(
        "uq_redencion_promocion_cupon",
        "redencion_promocion",
        ["id_cupon"],
        unique=True,
        postgresql_where=sa.text("id_cupon IS NOT NULL"),
    )
    op.create_index(
        "uq_redencion_promocion_oferta",
        "redencion_promocion",
        ["id_oferta_recompra"],
        unique=True,
        postgresql_where=sa.text("id_oferta_recompra IS NOT NULL"),
    )
    op.create_index(
        "uq_redencion_promocion_asignacion",
        "redencion_promocion",
        ["id_asignacion_experimento"],
        unique=True,
        postgresql_where=sa.text("id_asignacion_experimento IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("redencion_promocion")
    op.drop_index("ix_asignacion_experimento_id_cliente", table_name="asignacion_experimento")
    op.drop_table("asignacion_experimento")
    op.drop_index("ix_experimento_reactivacion_veredicto", table_name="experimento_reactivacion")
    op.drop_index("ix_experimento_reactivacion_id_campania", table_name="experimento_reactivacion")
    op.drop_table("experimento_reactivacion")
    op.drop_index("ix_oferta_recompra_id_cliente", table_name="oferta_recompra")
    op.drop_index("ix_oferta_recompra_estado_reserva_hasta", table_name="oferta_recompra")
    op.drop_index("uq_oferta_recompra_activa", table_name="oferta_recompra")
    op.drop_table("oferta_recompra")
    op.drop_index("ix_cupon_id_cliente", table_name="cupon")
    op.drop_index("ix_cupon_estado_valido_hasta", table_name="cupon")
    op.drop_table("cupon")
    op.drop_index("ix_campania_tipo", table_name="campania")
    op.drop_table("campania")
