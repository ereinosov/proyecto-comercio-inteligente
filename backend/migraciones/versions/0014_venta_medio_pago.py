"""Venta: id_medio_pago — medio de pago elegido por el cliente en el POS (enmienda v2.7.2).

Hasta ahora el POS no registraba con qué pagaba el cliente: la `venta` sólo llevaba una
`referencia_terminal_pago` opaca, y la factura simulada de 009 deducía el medio con una
heurística de dos valores (con referencia → "tarjeta", sin ella → "efectivo"). Esta migración
añade `venta.id_medio_pago`, FK NULL-able al catálogo `medio_pago` de 007, para guardar la
CATEGORÍA real del pago que se selecciona en la pantalla de Venta.

Cambio de esquema ADITIVO PURO sobre una entidad certificada de 001:

  * `venta.id_medio_pago` es NULL-able y sin default. Ninguna venta histórica se toca
    (todas quedan con `NULL`), y todo consumidor de `venta` que no lo conozca sigue igual.
  * La factura simulada de 009 usa el nombre del medio cuando la venta lo declara y CAE a la
    heurística previa cuando es `NULL` — 009 no cambia su esquema.
  * Es la categoría del pago, NUNCA un dato de instrumento (PAN/CVV/banda siguen fuera de
    todo módulo, Principio IV / Restricciones Técnicas).

Reversión (`downgrade`): elimina la columna. Se pierde el medio declarado en las ventas
posteriores a la enmienda — pérdida aceptada y documentada (la factura vuelve a la heurística).

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("venta", sa.Column("id_medio_pago", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_venta_medio_pago",
        "venta",
        "medio_pago",
        ["id_medio_pago"],
        ["id_medio_pago"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_venta_medio_pago", "venta", type_="foreignkey")
    op.drop_column("venta", "id_medio_pago")
