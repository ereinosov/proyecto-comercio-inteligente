"""Fixtures compartidas. Las pruebas de integración y de contrato corren contra PostgreSQL
real en una base de datos de pruebas separada (`rasero_test`), recreada y migrada con Alembic
al inicio de la sesión — nunca contra SQLite (constitución, Restricciones Técnicas).
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
sys.path.insert(0, str(BACKEND))

TEST_DB_URL = "postgresql+psycopg://rasero@localhost:5442/rasero_test"
os.environ["DATABASE_URL"] = TEST_DB_URL


def pytest_configure(config):
    from sqlalchemy import create_engine, text

    admin_engine = create_engine(
        "postgresql+psycopg://rasero@localhost:5442/postgres", isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS rasero_test WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE rasero_test"))
    admin_engine.dispose()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "migraciones" / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migraciones"))
    command.upgrade(cfg, "head")


import pytest  # noqa: E402


@pytest.fixture
def sesion():
    from rasero.persistencia.sesion import SesionLocal

    s = SesionLocal()
    try:
        yield s
    finally:
        s.close()
