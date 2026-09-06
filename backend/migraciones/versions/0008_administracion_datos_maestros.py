"""Administración de datos maestros: campo `activo` en sucursal, producto, categoria y
zona_exhibicion (medio_pago ya lo tiene desde 0007).

Cierra la brecha entre lo que el modelo promete (Rasero soporta N sucursales sin cambios
estructurales — constitución, "Modelo multi-sucursal") y lo que la interfaz permitía (estos
maestros sólo se creaban editando un script de semilla de Python). El borrado nunca es físico
(Principio IV: el estado debe ser reconstruible): la UI "Desactivar" pone `activo = false`,
mismo precedente que `operador.activo` desde el esquema inicial.

No se añaden otros campos: cada uno de estos modelos ya tiene todos los atributos que un
formulario de alta completo necesita (sucursal: nombre, zona_horaria; categoria: nombre,
dias_umbral_inmovilizado; producto: id_categoria, nombre, es_granel, precio_vigente,
lleva_caducidad, moneda; zona_exhibicion: id_sucursal, nombre, grado_privilegio).

Reversión: `DROP COLUMN activo` en las cuatro tablas.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLAS = ("sucursal", "producto", "categoria", "zona_exhibicion")


def upgrade() -> None:
    for tabla in _TABLAS:
        op.add_column(
            tabla,
            sa.Column(
                "activo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
        # El server_default sólo hacía falta para poblar las filas existentes; el modelo
        # declara default de aplicación, igual que `operador.activo`.
        op.alter_column(tabla, "activo", server_default=None)


def downgrade() -> None:
    for tabla in reversed(_TABLAS):
        op.drop_column(tabla, "activo")
