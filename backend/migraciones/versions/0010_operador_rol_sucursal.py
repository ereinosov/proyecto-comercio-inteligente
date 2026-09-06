"""Operador: rol de 3 valores y sucursal fija — User Story 10 de 001-core-ventas-inventario
(Principio VI, enmienda constitucional v2.3.0).

Cambio de esquema sobre una entidad YA CERTIFICADA de 001:

  * Añade `operador.id_sucursal INTEGER NOT NULL` (FK -> sucursal). Relación uno-a-uno: un
    operador pertenece a exactamente una sucursal fija.
  * Añade `operador.rol TEXT NOT NULL CHECK (rol IN ('cajero','encargado','admin'))` y RETIRA
    la columna booleana `operador.es_encargado`.

Migración de datos (regla de conversión EXPLÍCITA — no se infiere ningún admin):

    es_encargado = FALSE  ->  rol = 'cajero'
    es_encargado = TRUE   ->  rol = 'encargado'

    NINGÚN operador existente pasa a 'admin'. El rol 'admin' se crea siempre de forma explícita
    (semilla o alta desde la interfaz por otro admin).

  * `id_sucursal` de cada operador existente se deriva de la sucursal de su turno más reciente
    (`turno.instante_apertura` máximo); si el operador no tiene ningún turno, se le asigna la
    primera sucursal por `id_sucursal`. Nunca queda NULL.

Reversión (`downgrade`): recrea `es_encargado BOOLEAN NOT NULL DEFAULT FALSE`, lo rellena con
`rol IN ('encargado','admin') -> TRUE` y el resto `FALSE`, y elimina `rol` e `id_sucursal`.
Un operador que hubiera sido 'admin' se revierte a `es_encargado = TRUE` (el modelo viejo no
distingue admin de encargado); es una pérdida de información aceptada y documentada.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- id_sucursal ------------------------------------------------------
    op.add_column("operador", sa.Column("id_sucursal", sa.Integer(), nullable=True))
    # Sucursal del turno más reciente de cada operador.
    op.execute(
        """
        UPDATE operador AS o
        SET id_sucursal = t.id_sucursal
        FROM (
            SELECT DISTINCT ON (id_operador) id_operador, id_sucursal
            FROM turno
            ORDER BY id_operador, instante_apertura DESC
        ) AS t
        WHERE t.id_operador = o.id_operador
        """
    )
    # Operadores sin ningún turno -> primera sucursal por id_sucursal.
    op.execute(
        """
        UPDATE operador
        SET id_sucursal = (SELECT id_sucursal FROM sucursal ORDER BY id_sucursal LIMIT 1)
        WHERE id_sucursal IS NULL
        """
    )
    op.alter_column("operador", "id_sucursal", nullable=False)
    op.create_foreign_key(
        "fk_operador_sucursal", "operador", "sucursal", ["id_sucursal"], ["id_sucursal"]
    )

    # --- rol (reemplaza es_encargado) -----------------------------------
    op.add_column("operador", sa.Column("rol", sa.String(), nullable=True))
    # Regla de conversión EXPLÍCITA:
    #   es_encargado = FALSE -> 'cajero'
    #   es_encargado = TRUE  -> 'encargado'
    #   (ningún 'admin' automático)
    op.execute("UPDATE operador SET rol = 'encargado' WHERE es_encargado = TRUE")
    op.execute("UPDATE operador SET rol = 'cajero' WHERE es_encargado = FALSE")
    op.alter_column("operador", "rol", nullable=False)
    op.create_check_constraint(
        "ck_operador_rol", "operador", "rol IN ('cajero','encargado','admin')"
    )
    op.drop_column("operador", "es_encargado")


def downgrade() -> None:
    op.add_column(
        "operador",
        sa.Column("es_encargado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # 'encargado' y 'admin' -> TRUE (el modelo viejo no distingue admin de encargado).
    op.execute("UPDATE operador SET es_encargado = TRUE WHERE rol IN ('encargado', 'admin')")
    op.alter_column("operador", "es_encargado", server_default=None)

    op.drop_constraint("ck_operador_rol", "operador", type_="check")
    op.drop_column("operador", "rol")

    op.drop_constraint("fk_operador_sucursal", "operador", type_="foreignkey")
    op.drop_column("operador", "id_sucursal")
