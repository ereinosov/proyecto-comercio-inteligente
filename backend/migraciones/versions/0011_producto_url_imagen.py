"""Producto: url_imagen — User Story 12 de 001-core-ventas-inventario.

Añade `producto.url_imagen TEXT NULL`: la URL externa de una imagen del producto que el
catálogo en grid de la pantalla de Venta muestra por tarjeta. Opcional — un producto sin URL
(o con una URL que falla al cargar, resuelto en el frontend con `onError`) cae al ícono de
familia de categoría que ya existe (La Regla del Ícono por Categoría, DESIGN.md v1.2.0).

Cambio de esquema ADITIVO PURO sobre una entidad ya certificada de 001:

  * `producto.url_imagen` es NULL-able y sin default. Ningún consumidor existente de `producto`
    (venta, inventario, precios, pronóstico, promociones) lee esta columna; todos siguen
    funcionando sin conocerla.
  * No hay migración de datos: todas las filas quedan con `url_imagen = NULL`.

Reversión (`downgrade`): elimina la columna. Se pierde cualquier URL configurada — pérdida de
información aceptada y documentada (el dato es puramente presentacional y reconstruible desde
Administración).

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("producto", sa.Column("url_imagen", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("producto", "url_imagen")
