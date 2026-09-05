"""Esquema inicial: las 20 tablas de data-model.md (constitución v2.2.0).

Revision ID: 0001
Revises:
Create Date: 2026-09-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sucursal",
        sa.Column("id_sucursal", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False, unique=True),
        sa.Column("zona_horaria", sa.String(), nullable=False),
    )

    op.create_table(
        "categoria",
        sa.Column("id_categoria", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False, unique=True),
        sa.Column("dias_umbral_inmovilizado", sa.Integer(), nullable=True),
    )

    op.create_table(
        "producto",
        sa.Column("id_producto", sa.Integer(), primary_key=True),
        sa.Column("id_categoria", sa.Integer(), sa.ForeignKey("categoria.id_categoria"), nullable=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("es_granel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("precio_vigente", sa.Numeric(12, 4), nullable=False),
        sa.Column("lleva_caducidad", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
    )

    op.create_table(
        "producto_precio_sucursal",
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), primary_key=True),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), primary_key=True),
        sa.Column("precio_vigente", sa.Numeric(12, 4), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
    )

    op.create_table(
        "zona_exhibicion",
        sa.Column("id_zona_exhibicion", sa.Integer(), primary_key=True),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("grado_privilegio", sa.SmallInteger(), nullable=False),
    )

    op.create_table(
        "operador",
        sa.Column("id_operador", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("pin_hash", sa.String(), nullable=False),
        sa.Column("es_encargado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "turno",
        sa.Column("id_turno", sa.Integer(), primary_key=True),
        sa.Column("id_operador", sa.Integer(), sa.ForeignKey("operador.id_operador"), nullable=False),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("caja", sa.String(), nullable=False),
        sa.Column("instante_apertura", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instante_cierre", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "lote",
        sa.Column("id_lote", sa.Integer(), primary_key=True),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(12, 4), nullable=False),
        sa.Column("fecha_caducidad", sa.Date(), nullable=True),
        sa.Column("instante_entrada", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
    )
    op.create_index(
        "ix_lote_fefo",
        "lote",
        ["id_sucursal", "id_producto", "fecha_caducidad", "instante_entrada", "id_lote"],
    )

    op.create_table(
        "venta",
        sa.Column("id_venta", sa.BigInteger(), primary_key=True),
        sa.Column("clave_idempotencia", sa.String(), nullable=False, unique=True),
        sa.Column("id_turno", sa.Integer(), sa.ForeignKey("turno.id_turno"), nullable=False),
        sa.Column("referencia_terminal_pago", sa.String(), nullable=True),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
    )

    op.create_table(
        "traspaso",
        sa.Column("id_traspaso", sa.Integer(), primary_key=True),
        sa.Column("id_sucursal_origen", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("id_sucursal_destino", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("estado", sa.String(), nullable=False, server_default="en_transito"),
        sa.Column("instante_despacho", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instante_recepcion", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id_sucursal_origen <> id_sucursal_destino", name="ck_traspaso_distinto"),
        sa.CheckConstraint("estado IN ('en_transito','recibido')", name="ck_traspaso_estado"),
    )

    op.create_table(
        "conteo_fisico",
        sa.Column("id_conteo_fisico", sa.Integer(), primary_key=True),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("estado", sa.String(), nullable=False, server_default="abierto"),
        sa.Column("alcance", postgresql.JSONB(), nullable=True),
        sa.Column("instante_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instante_resolucion", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("estado IN ('abierto','resuelto')", name="ck_conteo_estado"),
    )

    op.create_table(
        "anulacion_venta",
        sa.Column("id_anulacion_venta", sa.BigInteger(), primary_key=True),
        sa.Column("id_venta", sa.BigInteger(), sa.ForeignKey("venta.id_venta"), nullable=False, unique=True),
        sa.Column("id_operador", sa.Integer(), sa.ForeignKey("operador.id_operador"), nullable=False),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.String(), nullable=True),
    )

    op.create_table(
        "renglon_venta",
        sa.Column("id_renglon_venta", sa.BigInteger(), primary_key=True),
        sa.Column("id_venta", sa.BigInteger(), sa.ForeignKey("venta.id_venta"), nullable=False),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("cantidad_unidades", sa.Integer(), nullable=True),
        sa.Column("cantidad_gramos", sa.Integer(), nullable=True),
        sa.Column("precio_aplicado", sa.Numeric(12, 4), nullable=False),
        sa.Column("importe", sa.Numeric(12, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
        sa.CheckConstraint(
            "(CASE WHEN cantidad_unidades IS NOT NULL THEN 1 ELSE 0 END"
            " + CASE WHEN cantidad_gramos IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_renglon_una_cantidad",
        ),
        sa.CheckConstraint(
            "(cantidad_unidades IS NULL OR cantidad_unidades > 0)"
            " AND (cantidad_gramos IS NULL OR cantidad_gramos > 0)",
            name="ck_renglon_cantidad_positiva",
        ),
    )

    op.create_table(
        "movimiento_inventario",
        sa.Column("id_movimiento_inventario", sa.BigInteger(), primary_key=True),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_lote", sa.Integer(), sa.ForeignKey("lote.id_lote"), nullable=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("cantidad", sa.Numeric(14, 0), nullable=False),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_venta", sa.BigInteger(), sa.ForeignKey("venta.id_venta"), nullable=True),
        sa.Column("id_traspaso", sa.Integer(), sa.ForeignKey("traspaso.id_traspaso"), nullable=True),
        sa.Column(
            "id_conteo_fisico", sa.Integer(), sa.ForeignKey("conteo_fisico.id_conteo_fisico"), nullable=True
        ),
        sa.Column(
            "id_anulacion_venta",
            sa.BigInteger(),
            sa.ForeignKey("anulacion_venta.id_anulacion_venta"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "tipo IN ('entrada_compra','salida_venta','entrada_anulacion',"
            "'salida_traspaso','entrada_traspaso','ajuste_conteo')",
            name="ck_movimiento_tipo",
        ),
        sa.CheckConstraint(
            "(tipo = 'entrada_compra' AND id_venta IS NULL AND id_traspaso IS NULL"
            "   AND id_conteo_fisico IS NULL AND id_anulacion_venta IS NULL)"
            " OR (tipo = 'salida_venta' AND id_venta IS NOT NULL AND id_traspaso IS NULL"
            "   AND id_conteo_fisico IS NULL AND id_anulacion_venta IS NULL)"
            " OR (tipo = 'entrada_anulacion' AND id_anulacion_venta IS NOT NULL"
            "   AND id_venta IS NULL AND id_traspaso IS NULL AND id_conteo_fisico IS NULL)"
            " OR (tipo IN ('salida_traspaso','entrada_traspaso') AND id_traspaso IS NOT NULL"
            "   AND id_venta IS NULL AND id_conteo_fisico IS NULL AND id_anulacion_venta IS NULL)"
            " OR (tipo = 'ajuste_conteo' AND id_conteo_fisico IS NOT NULL"
            "   AND id_venta IS NULL AND id_traspaso IS NULL AND id_anulacion_venta IS NULL)",
            name="ck_movimiento_origen_unico",
        ),
    )
    op.create_index(
        "ix_movimiento_sucursal_producto", "movimiento_inventario", ["id_sucursal", "id_producto"]
    )

    # existencia: PostgreSQL prohíbe columnas NULL en una PRIMARY KEY. data-model.md declaraba
    # id_lote nulo como parte de la PK compuesta, lo cual es contradictorio; se corrige con una
    # clave sustituta más UNIQUE NULLS NOT DISTINCT (PG15+), que sí admite NULL tratando todos
    # los NULL como equivalentes entre sí — el mismo efecto que una PK, con NULL admitido.
    op.create_table(
        "existencia",
        sa.Column("id_existencia", sa.BigInteger(), primary_key=True),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_lote", sa.Integer(), sa.ForeignKey("lote.id_lote"), nullable=True),
        sa.Column("cantidad", sa.Numeric(14, 0), nullable=False, server_default="0"),
    )
    op.execute(
        "ALTER TABLE existencia ADD CONSTRAINT uq_existencia_identidad "
        "UNIQUE NULLS NOT DISTINCT (id_sucursal, id_producto, id_lote)"
    )

    op.create_table(
        "consulta_no_atendida",
        sa.Column("id_consulta_no_atendida", sa.BigInteger(), primary_key=True),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("id_turno", sa.Integer(), sa.ForeignKey("turno.id_turno"), nullable=False),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.Column("saldo_en_el_instante", sa.Numeric(14, 0), nullable=False),
    )

    op.create_table(
        "canal_competencia",
        sa.Column("id_canal_competencia", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("nombre_normalizado", sa.String(), nullable=False, unique=True),
    )

    op.create_table(
        "observacion_precio",
        sa.Column("id_observacion_precio", sa.BigInteger(), primary_key=True),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column(
            "id_canal_competencia",
            sa.Integer(),
            sa.ForeignKey("canal_competencia.id_canal_competencia"),
            nullable=False,
        ),
        sa.Column("presentacion_cantidad", sa.Numeric(12, 3), nullable=False),
        sa.Column("presentacion_unidad", sa.String(), nullable=False),
        sa.Column("precio_observado", sa.Numeric(12, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("fuente", sa.String(), nullable=False),
        sa.Column("origen_captura", sa.String(), nullable=False),
        sa.Column("instante_captura", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_turno", sa.Integer(), sa.ForeignKey("turno.id_turno"), nullable=True),
        sa.Column("comparable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "presentacion_unidad IN ('unidad','gramo','mililitro')",
            name="ck_observacion_presentacion_unidad",
        ),
        sa.CheckConstraint("origen_captura IN ('manual','archivo')", name="ck_observacion_origen_captura"),
    )

    op.create_table(
        "conteo_renglon",
        sa.Column("id_conteo_renglon", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_conteo_fisico", sa.Integer(), sa.ForeignKey("conteo_fisico.id_conteo_fisico"), nullable=False
        ),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_lote", sa.Integer(), sa.ForeignKey("lote.id_lote"), nullable=True),
        sa.Column("cantidad_contada", sa.Numeric(14, 0), nullable=False),
        sa.Column("cantidad_esperada", sa.Numeric(14, 0), nullable=False),
        sa.Column("diferencia", sa.Numeric(14, 0), nullable=False),
    )

    op.create_table(
        "operacion_pendiente",
        sa.Column("id_operacion_pendiente", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tipo_operacion", sa.String(), nullable=False),
        sa.Column("carga", postgresql.JSONB(), nullable=False),
        sa.Column("recurso_afectado", sa.String(), nullable=False),
        sa.Column("marca_tiempo_origen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instante_recepcion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente_de_sincronizar"),
        sa.Column(
            "id_operacion_prevaleciente",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operacion_pendiente.id_operacion_pendiente"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "tipo_operacion IN ('venta','consulta_no_atendida','anulacion_venta',"
            "'recepcion_traspaso','resolucion_conteo')",
            name="ck_operacion_pendiente_tipo",
        ),
        sa.CheckConstraint(
            "estado IN ('pendiente_de_sincronizar','sincronizada','conflicto_resuelto')",
            name="ck_operacion_pendiente_estado",
        ),
    )


def downgrade() -> None:
    op.drop_table("operacion_pendiente")
    op.drop_table("conteo_renglon")
    op.drop_table("observacion_precio")
    op.drop_table("canal_competencia")
    op.drop_table("consulta_no_atendida")
    op.drop_table("existencia")
    op.drop_index("ix_movimiento_sucursal_producto", table_name="movimiento_inventario")
    op.drop_table("movimiento_inventario")
    op.drop_table("renglon_venta")
    op.drop_table("anulacion_venta")
    op.drop_table("conteo_fisico")
    op.drop_table("traspaso")
    op.drop_table("venta")
    op.drop_index("ix_lote_fefo", table_name="lote")
    op.drop_table("lote")
    op.drop_table("turno")
    op.drop_table("operador")
    op.drop_table("zona_exhibicion")
    op.drop_table("producto_precio_sucursal")
    op.drop_table("producto")
    op.drop_table("categoria")
    op.drop_table("sucursal")
