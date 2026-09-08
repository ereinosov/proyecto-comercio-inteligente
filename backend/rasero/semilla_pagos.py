"""Datos de demostración de 007-pagos-seguridad: cobertura de medios de pago por sucursal.

El catálogo `medio_pago` lo siembra la migración 0007 (`cfg.MEDIOS_PAGO_BASE`), pero **ningún
seed declaraba qué medios acepta cada sucursal ni desde cuándo** (`cobertura_pago`). Sin esos
tramos, `cobertura_en_fecha` devuelve `False` para todo y la pantalla "Pagos / Cobertura" se ve
incoherente frente a Venta, que sí cobra en efectivo. Este seed cierra ese hueco de datos —no
cambia ninguna lógica de negocio— declarando que **cada sucursal acepta todos los medios base**
desde la apertura simulada del comercio.

Uso:  python -m rasero.semilla_pagos     (después de `python -m rasero.semilla`)

Idempotente: un par (sucursal, medio) que ya tiene un tramo vigente (`fecha_hasta IS NULL`) se
salta.
"""

from datetime import date

from sqlalchemy import select

from rasero.persistencia.modelos import CoberturaPago, MedioPago, Operador, Sucursal
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.cobertura_pago import declarar_cobertura

# Apertura simulada del comercio: anterior a cualquier movimiento de las otras semillas.
APERTURA_COMERCIO = date(2026, 1, 1)


def sembrar() -> dict:
    sesion = SesionLocal()
    try:
        operador = sesion.execute(
            select(Operador).where(Operador.rol.in_(("encargado", "admin")), Operador.activo)
        ).scalars().first()
        if operador is None:
            print(
                "No hay ningún operador con rol encargado o admin. "
                "Ejecuta primero `python -m rasero.semilla`."
            )
            return {"tramos_creados": 0, "sucursales": 0, "medios": 0}

        sucursales = list(sesion.execute(select(Sucursal)).scalars())
        medios = list(sesion.execute(select(MedioPago).where(MedioPago.activo)).scalars())
        if not sucursales or not medios:
            print("Faltan sucursales o medios de pago. Ejecuta primero `python -m rasero.semilla`.")
            return {"tramos_creados": 0, "sucursales": len(sucursales), "medios": len(medios)}

        creados = 0
        for sucursal in sucursales:
            for medio in medios:
                ya = sesion.execute(
                    select(CoberturaPago).where(
                        CoberturaPago.id_sucursal == sucursal.id_sucursal,
                        CoberturaPago.id_medio_pago == medio.id_medio_pago,
                        CoberturaPago.fecha_hasta.is_(None),
                    )
                ).scalar_one_or_none()
                if ya is not None:
                    continue
                declarar_cobertura(
                    sesion,
                    id_sucursal=sucursal.id_sucursal,
                    id_medio_pago=medio.id_medio_pago,
                    acepta=True,
                    fecha_desde=APERTURA_COMERCIO,
                    operador=operador,
                )
                creados += 1

        sesion.commit()
        print(
            f"Cobertura de pagos sembrada: {creados} tramos nuevos "
            f"({len(sucursales)} sucursales × {len(medios)} medios, desde {APERTURA_COMERCIO})."
        )
        return {
            "tramos_creados": creados,
            "sucursales": len(sucursales),
            "medios": len(medios),
        }
    finally:
        sesion.close()


if __name__ == "__main__":
    sembrar()
