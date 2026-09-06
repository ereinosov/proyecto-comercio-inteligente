"""User Story 10 (Principio VI, enmienda v2.3.0): la migración de datos 0010 convierte los
operadores del modelo viejo (`es_encargado` booleano) al nuevo (`rol` + `id_sucursal`) con la
regla EXACTA `false -> cajero`, `true -> encargado`, y NUNCA crea un `admin` automático.

Prueba obligatoria (Principio III): transición de esquema sobre una entidad certificada de 001.
Baja a la revisión 0009, inserta filas del modelo viejo por SQL, vuelve a subir a `head` y
comprueba el resultado. Restaura `head` al final para no dejar la base de pruebas a media
migración.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from rasero.persistencia.sesion import engine
from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[2] / "backend"


def _alembic_cfg() -> Config:
    cfg = Config(str(BACKEND / "migraciones" / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migraciones"))
    return cfg


@pytest.fixture
def base_en_0009():
    cfg = _alembic_cfg()
    command.downgrade(cfg, "0009")
    try:
        yield
    finally:
        command.upgrade(cfg, "head")


def test_conversion_de_es_encargado_a_rol(base_en_0009):
    cfg = _alembic_cfg()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO sucursal (nombre, zona_horaria, activo) VALUES ('Mig A', 'America/Guayaquil', true)")
        )
        s2 = conn.execute(
            text("INSERT INTO sucursal (nombre, zona_horaria, activo) VALUES ('Mig B', 'America/Guayaquil', true) RETURNING id_sucursal")
        ).scalar_one()
        # Un cajero (con turno en s2) y un encargado (sin turnos).
        op_cajero = conn.execute(text(
            "INSERT INTO operador (nombre, pin_hash, es_encargado, activo) "
            "VALUES ('Mig Cajero', '', false, true) RETURNING id_operador"
        )).scalar_one()
        op_encargado = conn.execute(text(
            "INSERT INTO operador (nombre, pin_hash, es_encargado, activo) "
            "VALUES ('Mig Encargado', '', true, true) RETURNING id_operador"
        )).scalar_one()
        conn.execute(text(
            "INSERT INTO turno (id_operador, id_sucursal, caja, instante_apertura) "
            "VALUES (:op, :suc, 'caja-1', now())"
        ), {"op": op_cajero, "suc": s2})

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        filas = dict(conn.execute(text(
            "SELECT id_operador, rol FROM operador WHERE id_operador IN (:a, :b)"
        ), {"a": op_cajero, "b": op_encargado}).all())
        sucursal_cajero = conn.execute(text(
            "SELECT id_sucursal FROM operador WHERE id_operador = :a"
        ), {"a": op_cajero}).scalar_one()
        sucursal_encargado = conn.execute(text(
            "SELECT id_sucursal FROM operador WHERE id_operador = :b"
        ), {"b": op_encargado}).scalar_one()
        n_admin = conn.execute(text("SELECT count(*) FROM operador WHERE rol = 'admin'")).scalar_one()
        n_sin_sucursal = conn.execute(text("SELECT count(*) FROM operador WHERE id_sucursal IS NULL")).scalar_one()

    assert filas[op_cajero] == "cajero"          # es_encargado = false
    assert filas[op_encargado] == "encargado"    # es_encargado = true
    assert n_admin == 0                          # ningún admin automático (SC-012)
    assert n_sin_sucursal == 0                   # toda id_sucursal quedó no nula
    assert sucursal_cajero == s2                 # sucursal del turno más reciente
    assert sucursal_encargado is not None        # sin turnos -> primera sucursal activa, nunca NULL


def test_downgrade_es_reversible(base_en_0009):
    cfg = _alembic_cfg()
    # 0009 -> head -> 0009 -> head sin error; en 0009 la columna vieja existe.
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0009")
    with engine.connect() as conn:
        cols = {
            r[0]
            for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'operador'"
            )).all()
        }
    assert "es_encargado" in cols
    assert "rol" not in cols
    assert "id_sucursal" not in cols
