"""Identificador de cliente (cédula o RUC de persona natural) para evitar duplicados entre
visitas — User Story 4 de 002-clientes-fidelizacion (FR-017).

Añade `cliente.identificador TEXT NULL`. El nombre de columna es "identificador" y no "cedula"
a propósito: cubre los dos casos admitidos (cédula de 10 dígitos o RUC natural de 13) sin
implicar uno solo.

Índice único PARCIAL `WHERE identificador IS NOT NULL AND anonimizado = false`:

  * `identificador IS NOT NULL` — múltiples clientes SIN identificador (el caso normal:
    consumidor final, o cajero que no lo pidió) siguen siendo válidos. La unicidad sólo aplica
    a los que sí lo tienen.
  * `AND anonimizado = false` — DECISIÓN: el índice excluye a los clientes anonimizados, para
    que una cédula quede libre y pueda reasignarse después de que su titular fue anonimizado
    (FR-015/FR-016). Coincide con la semántica del chequeo 409 del endpoint ("ya existe en otro
    cliente ACTIVO"). La tarea de anonimización además pone `identificador = NULL`
    (`servicios/anonimizacion.py`), así que en la práctica el predicado `IS NOT NULL` ya bastaría;
    el `AND anonimizado = false` se deja explícito como defensa en profundidad y para que la
    intención viva en el esquema, no sólo en el código de aplicación.

Reversión: `DROP INDEX` + `DROP COLUMN`.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cliente", sa.Column("identificador", sa.String(), nullable=True))
    op.execute(
        "CREATE UNIQUE INDEX uq_cliente_identificador ON cliente (identificador) "
        "WHERE identificador IS NOT NULL AND anonimizado = false"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_cliente_identificador")
    op.drop_column("cliente", "identificador")
