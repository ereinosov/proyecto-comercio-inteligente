"""Cupón: estado 'anulado' — permitir anular un cupón generado que no se llegó a redimir.

La pantalla de Promociones no tenía forma de deshacer una campaña de cupones ("en caso de
arrepentirse"). Esta migración amplía el CHECK de `cupon.estado` para admitir 'anulado'
además de 'generado' / 'redimido' / 'vencido'. Un cupón redimido —que ya afectó una venta—
NO se puede anular; eso lo valida el servicio.

Cambio ADITIVO: ningún cupón existente cambia de estado. `downgrade` restaura el CHECK
anterior; falla si a esas alturas hay cupones en 'anulado' (habría que resolverlos antes).

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_cupon_estado", "cupon", type_="check")
    op.create_check_constraint(
        "ck_cupon_estado",
        "cupon",
        "estado IN ('generado','redimido','vencido','anulado')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cupon_estado", "cupon", type_="check")
    op.create_check_constraint(
        "ck_cupon_estado",
        "cupon",
        "estado IN ('generado','redimido','vencido')",
    )
