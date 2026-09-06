"""Pagos y seguridad: medio_pago, terminal_pago, cobertura_pago, bitacora_auditoria, token_pago
(data-model.md de 007-pagos-seguridad, constitución v2.2.6).

Cuatro preocupaciones acotadas del encargo (FR-033), cada una con su registro:
- `medio_pago` — catálogo global de medios de pago.
- `terminal_pago` — datáfono físico, versión de firmware, historia de ubicación. Los indicadores
  "desactualizada"/"expuesta a clonación" son cálculo derivado al leer, NO columnas (research.md #3).
- `cobertura_pago` — aceptación histórica de un medio en una sucursal (tramos de vigencia sin
  solape). La cuota de intención no atendida se deriva de `bitacora_auditoria` (research.md #5).
- `bitacora_auditoria` — rastro de SOLO ANEXADO de los hechos de pago (Principio IV, FR-025).
- `token_pago` — registro autoritativo de un cobro con tarjeta tokenizado. `UNIQUE (id_venta)` (un
  token por cobro) + `UNIQUE (clave_idempotencia)` (research.md #1, #15). SIN ningún campo de PAN,
  CVV o banda/chip; `ultimos_digitos CHAR(4)` con CHECK de 4 dígitos (barrera de esquema, FR-018).

Entidad `token_pago` añadida por la enmienda constitucional v2.2.6 (research.md #1).

DESVIACIÓN DOCUMENTADA de tasks.md T001: el append-only de `bitacora_auditoria` se hace con un
TRIGGER `BEFORE UPDATE OR DELETE` que lanza excepción (rechazo del motor, T039), NO con
`REVOKE ... FROM rasero_app` — en este entorno el rol de BD es `rasero` (dueño de las tablas y
superusuario en desarrollo), sobre el que un REVOKE no surte efecto. El trigger cumple la misma
intención ("append-only forzado por el motor, no sólo por la aplicación") de forma portable.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from rasero.config import pagos as cfg

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MARCA = "marca IN ('visa','mastercard','amex','diners','otra')"
_TIPO = "tipo IN ('debito','credito','desconocido')"
_INICIADOR = "iniciador_tipo IN ('operador','proceso')"
_TIPO_EVENTO = (
    "tipo_evento IN ('token_emitido','token_idempotencia_divergente','token_purgado',"
    "'pan_rechazado','firmware_actualizado','firmware_desactualizado_detectado',"
    "'terminal_expuesta_detectada','terminal_registrada','terminal_movida','medio_pago_alta',"
    "'medio_pago_baja','cobertura_declarada','intencion_no_atendida','config_firmware_cambiada')"
)
_REFERENCIA = (
    "referencia_recurso_tipo IS NULL OR referencia_recurso_tipo IN "
    "('token_pago','venta','terminal_pago','medio_pago','cobertura_pago')"
)

_TRIGGER_BITACORA = """
CREATE OR REPLACE FUNCTION bitacora_auditoria_solo_anexado()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'bitacora_auditoria es de solo anexado: no se admite % (Principio IV, FR-025)',
        TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bitacora_auditoria_solo_anexado
BEFORE UPDATE OR DELETE ON bitacora_auditoria
FOR EACH ROW EXECUTE FUNCTION bitacora_auditoria_solo_anexado();
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "medio_pago",
        sa.Column("id_medio_pago", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False, unique=True),
        sa.Column("requiere_terminal", sa.Boolean(), nullable=False),
        sa.Column("admite_tokenizacion", sa.Boolean(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "terminal_pago",
        sa.Column("id_terminal_pago", sa.Integer(), primary_key=True),
        sa.Column("identificador", sa.String(), nullable=False, unique=True),
        sa.Column("modelo", sa.String(), nullable=False),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column("version_firmware", sa.String(), nullable=False),
        sa.Column("fecha_ultima_actualizacion_firmware", sa.Date(), nullable=True),
        sa.Column(
            "historial_ubicacion", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "historial_firmware", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "id_operador_registro",
            sa.Integer(),
            sa.ForeignKey("operador.id_operador"),
            nullable=False,
        ),
        sa.Column("instante_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "version_firmware ~ '^[0-9]+\\.[0-9]+\\.[0-9]+$'", name="ck_terminal_pago_version"
        ),
    )
    op.create_index("ix_terminal_pago_sucursal", "terminal_pago", ["id_sucursal"])

    op.create_table(
        "cobertura_pago",
        sa.Column("id_cobertura_pago", sa.Integer(), primary_key=True),
        sa.Column(
            "id_medio_pago", sa.Integer(), sa.ForeignKey("medio_pago.id_medio_pago"), nullable=False
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column("fecha_desde", sa.Date(), nullable=False),
        sa.Column("fecha_hasta", sa.Date(), nullable=True),
        sa.Column(
            "id_operador", sa.Integer(), sa.ForeignKey("operador.id_operador"), nullable=False
        ),
        sa.Column("instante_registro", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "fecha_hasta IS NULL OR fecha_hasta >= fecha_desde", name="ck_cobertura_pago_periodo"
        ),
    )
    op.create_index(
        "ix_cobertura_pago_sucursal_fecha", "cobertura_pago", ["id_sucursal", "fecha_desde"]
    )
    # Regla de no solape de tramos de vigencia por (medio, sucursal) — research.md #5.
    op.execute(
        "ALTER TABLE cobertura_pago ADD CONSTRAINT ex_cobertura_pago_sin_solape "
        "EXCLUDE USING gist ("
        "id_medio_pago WITH =, id_sucursal WITH =, "
        "daterange(fecha_desde, COALESCE(fecha_hasta, 'infinity'::date), '[]') WITH &&)"
    )

    op.create_table(
        "bitacora_auditoria",
        sa.Column("id_bitacora_auditoria", sa.BigInteger(), primary_key=True),
        sa.Column("tipo_evento", sa.String(), nullable=False),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dia_local", sa.Date(), nullable=False),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column(
            "id_terminal_pago",
            sa.Integer(),
            sa.ForeignKey("terminal_pago.id_terminal_pago"),
            nullable=True,
        ),
        sa.Column(
            "id_medio_pago",
            sa.Integer(),
            sa.ForeignKey("medio_pago.id_medio_pago"),
            nullable=True,
        ),
        sa.Column("iniciador_tipo", sa.String(), nullable=False),
        sa.Column(
            "id_operador", sa.Integer(), sa.ForeignKey("operador.id_operador"), nullable=True
        ),
        sa.Column("proceso", sa.Text(), nullable=True),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("referencia_recurso_tipo", sa.String(), nullable=True),
        sa.Column("referencia_recurso_id", sa.Text(), nullable=True),
        sa.Column("clave_idempotencia", sa.Text(), nullable=True),
        sa.CheckConstraint(_TIPO_EVENTO, name="ck_bitacora_auditoria_tipo_evento"),
        sa.CheckConstraint(_INICIADOR, name="ck_bitacora_auditoria_iniciador"),
        sa.CheckConstraint(_REFERENCIA, name="ck_bitacora_auditoria_referencia"),
    )
    op.create_index(
        "ix_bitacora_auditoria_sucursal_dia", "bitacora_auditoria", ["id_sucursal", "dia_local"]
    )
    op.create_index(
        "ix_bitacora_auditoria_tipo_sucursal_dia",
        "bitacora_auditoria",
        ["tipo_evento", "id_sucursal", "dia_local"],
    )
    op.create_index(
        "ix_bitacora_auditoria_terminal",
        "bitacora_auditoria",
        ["id_terminal_pago"],
        postgresql_where=sa.text("id_terminal_pago IS NOT NULL"),
    )
    op.create_index(
        "uq_bitacora_auditoria_clave_idempotencia",
        "bitacora_auditoria",
        ["clave_idempotencia"],
        unique=True,
        postgresql_where=sa.text("clave_idempotencia IS NOT NULL"),
    )
    # Append-only forzado por el motor (ver docstring): trigger que rechaza UPDATE/DELETE.
    op.execute(_TRIGGER_BITACORA)

    op.create_table(
        "token_pago",
        sa.Column("id_token_pago", sa.BigInteger(), primary_key=True),
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        # FK de SOLO LECTURA a `venta` de 001; UNIQUE = un token por cobro (FR-016, research.md #1).
        sa.Column(
            "id_venta",
            sa.Integer(),
            sa.ForeignKey("venta.id_venta"),
            nullable=False,
            unique=True,
        ),
        sa.Column("clave_idempotencia", sa.Text(), nullable=False, unique=True),
        # Barrera de esquema contra FR-018: aquí no cabe un PAN completo.
        sa.Column("ultimos_digitos", sa.CHAR(4), nullable=False),
        sa.Column("marca", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column(
            "id_terminal_pago",
            sa.Integer(),
            sa.ForeignKey("terminal_pago.id_terminal_pago"),
            nullable=False,
        ),
        sa.Column(
            "id_sucursal", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False
        ),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dia_local", sa.Date(), nullable=False),
        sa.Column("marca_tiempo_origen", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ultimos_digitos ~ '^[0-9]{4}$'", name="ck_token_pago_ultimos_digitos"),
        sa.CheckConstraint(_MARCA, name="ck_token_pago_marca"),
        sa.CheckConstraint(_TIPO, name="ck_token_pago_tipo"),
    )
    op.create_index("ix_token_pago_sucursal_dia", "token_pago", ["id_sucursal", "dia_local"])

    # Siembra del catálogo de medios de pago (research.md #10).
    medio_pago = sa.table(
        "medio_pago",
        sa.column("nombre", sa.String),
        sa.column("requiere_terminal", sa.Boolean),
        sa.column("admite_tokenizacion", sa.Boolean),
        sa.column("activo", sa.Boolean),
    )
    op.bulk_insert(
        medio_pago,
        [{**m, "activo": True} for m in cfg.MEDIOS_PAGO_BASE],
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_bitacora_auditoria_solo_anexado ON bitacora_auditoria")
    op.execute("DROP FUNCTION IF EXISTS bitacora_auditoria_solo_anexado()")
    op.drop_index("ix_token_pago_sucursal_dia", table_name="token_pago")
    op.drop_table("token_pago")
    op.drop_index("uq_bitacora_auditoria_clave_idempotencia", table_name="bitacora_auditoria")
    op.drop_index("ix_bitacora_auditoria_terminal", table_name="bitacora_auditoria")
    op.drop_index("ix_bitacora_auditoria_tipo_sucursal_dia", table_name="bitacora_auditoria")
    op.drop_index("ix_bitacora_auditoria_sucursal_dia", table_name="bitacora_auditoria")
    op.drop_table("bitacora_auditoria")
    op.execute("ALTER TABLE cobertura_pago DROP CONSTRAINT ex_cobertura_pago_sin_solape")
    op.drop_index("ix_cobertura_pago_sucursal_fecha", table_name="cobertura_pago")
    op.drop_table("cobertura_pago")
    op.drop_index("ix_terminal_pago_sucursal", table_name="terminal_pago")
    op.drop_table("terminal_pago")
    op.drop_table("medio_pago")
