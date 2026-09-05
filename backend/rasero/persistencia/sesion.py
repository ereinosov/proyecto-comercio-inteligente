"""Engine y sesión SQLAlchemy contra PostgreSQL nativo (puerto 5442)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rasero.configuracion import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SesionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def obtener_sesion():
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()
