"""Datos de demostración de clientes y fidelización (002-clientes-fidelizacion).

    python -m rasero.semilla_clientes

Sirve para que **Clientes.tsx** muestre casos reales de cada estado en el examen, y para que el
**cupón de cumpleaños** de 005 tenga destinatarios:

  * ~45 clientes con `fecha_nacimiento` repartida por todo el año, ~8 de ellas dentro de los
    próximos 21 días (rango por defecto de "Generar cupones");
  * historial de visitas variado — clientes con `intervalo_compra` en estado `calculado`,
    clientes en `datos_insuficientes` (una o dos visitas), y un puñado con `senal_fuga`
    ACTIVA por inactividad, **fuera** del experimento de reactivación de 005;
  * valor de cliente calculable (frecuencia / monto / margen) para la mayoría.

Frontera de propiedad de datos (mismo principio que `rasero/semilla_reactivacion.py`): el
atrezo se construye **sólo** con servicios públicos — `registrar_cliente` y `registrar_visita`
de 002, `registrar_venta` de 001 — y `evaluar_fugas_pendientes` de 002 para las señales de
fuga. Nunca se escribe directo en `visita`, `intervalo_compra` ni `senal_fuga`. El catálogo y
la existencia los provee `rasero/semilla_catalogo.py`; este módulo los consume.

Idempotente: un cliente cuyo nombre ya existe no se vuelve a crear ni se le añaden visitas, y
`registrar_visita` es idempotente por `id_venta`.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Cliente, Operador, Producto, Sucursal, Turno
from rasero.persistencia.sesion import SesionLocal
from rasero.semilla_catalogo import SUCURSALES_DEMO
from rasero.semilla_catalogo import sembrar as sembrar_catalogo
from rasero.servicios.clientes import (
    evaluar_fugas_pendientes,
    registrar_cliente,
    registrar_visita,
)
from rasero.servicios.ventas import RenglonEntrada, registrar_venta

_SEMILLA = 20260905
_HOY = date(2026, 9, 5)

# Nombres de demostración. El prefijo hace obvio en la base que son atrezo de examen.
_PILA_NOMBRES = [
    "María Zambrano",
    "José Cedeño",
    "Gloria Macías",
    "Luis Vera",
    "Carmen Loor",
    "Ángel Bravo",
    "Rosa Mendoza",
    "Pedro Alcívar",
    "Juana Palma",
    "Carlos Intriago",
    "Elena Chávez",
    "Víctor Moreira",
    "Diana Solórzano",
    "Jorge Delgado",
    "Patricia Ponce",
    "Miguel Anchundia",
    "Sofía Vélez",
    "Raúl Menéndez",
    "Laura Pinargote",
    "Óscar Quijije",
    "Nadia Cañarte",
    "Iván Zamora",
    "Beatriz Andrade",
    "Fausto Rivera",
    "Lucía Tomalá",
    "Marco Saltos",
    "Tania Briones",
    "Hugo Parrales",
    "Silvia Choez",
    "Néstor Baque",
    "Adriana Franco",
    "Kevin Holguín",
    "Mónica Cevallos",
    "Édgar Villamar",
    "Paola Zavala",
    "Bruno Mero",
    "Verónica Lucas",
    "Danilo Ganchozo",
    "Karla Pico",
    "Ramiro Coello",
    "Yolanda Muñoz",
    "Freddy Cagua",
    "Estela Toala",
    "Wilson Pazmiño",
    "Gabriela Roldán",
]

# Perfiles de visita: (cantidad_de_visitas, dias_de_la_primera_atras, dias_de_la_ultima_atras).
# El estado de `intervalo_compra` lo decide 002 a partir de estos instantes.
_PERFIL_CALCULADO_ACTIVO = ("calculado_activo", 5, 150, 6)
_PERFIL_CALCULADO_FRECUENTE = ("calculado_frecuente", 8, 120, 3)
_PERFIL_FUGA = ("fuga_activa", 3, 170, 96)  # última compra > intervalo -> senal_fuga 'activa'
_PERFIL_INSUFICIENTE_2 = ("insuficiente_2", 2, 40, 12)
_PERFIL_INSUFICIENTE_1 = ("insuficiente_1", 1, 20, 20)

# Distribución de perfiles sobre los 45 clientes.
_DISTRIBUCION = (
    [_PERFIL_CALCULADO_ACTIVO] * 16
    + [_PERFIL_CALCULADO_FRECUENTE] * 10
    + [_PERFIL_FUGA] * 6
    + [_PERFIL_INSUFICIENTE_2] * 7
    + [_PERFIL_INSUFICIENTE_1] * 6
)


def _fecha_nacimiento(rng: random.Random, indice: int) -> date:
    """~8 de cada 45 caen dentro de los próximos 21 días (para el cupón de cumpleaños)."""
    anio = rng.randint(1962, 2001)
    if indice % 6 == 0:
        objetivo = _HOY + timedelta(days=rng.randint(0, 20))
        return date(anio, objetivo.month, objetivo.day)
    mes = rng.randint(1, 12)
    dia = rng.randint(1, 28)
    return date(anio, mes, dia)


def _turno_demo(sesion: Session) -> Turno:
    quevedo = sesion.execute(
        select(Sucursal).where(Sucursal.nombre == "Quevedo Centro")
    ).scalar_one()
    turno = sesion.execute(
        select(Turno)
        .where(Turno.id_sucursal == quevedo.id_sucursal, Turno.instante_cierre.is_(None))
        .order_by(Turno.id_turno)
        .limit(1)
    ).scalar_one_or_none()
    if turno is not None:
        return turno
    operador = sesion.execute(select(Operador).order_by(Operador.id_operador)).scalars().first()
    turno = Turno(
        id_operador=operador.id_operador,
        id_sucursal=quevedo.id_sucursal,
        caja="caja-semilla",
        instante_apertura=datetime.now(timezone.utc) - timedelta(days=200),
    )
    sesion.add(turno)
    sesion.flush()
    sesion.commit()
    return turno


def _productos_baratos(sesion: Session) -> list[Producto]:
    return list(
        sesion.execute(
            select(Producto).where(Producto.es_granel.is_(False)).order_by(Producto.id_producto)
        ).scalars()
    )[:12]


def _una_venta(
    sesion: Session,
    *,
    turno: Turno,
    productos: list[Producto],
    rng: random.Random,
    instante: datetime,
    clave: str,
) -> int:
    elegidos = rng.sample(productos, k=rng.randint(1, 3))
    renglones = [
        RenglonEntrada(
            id_producto=p.id_producto, cantidad_unidades=rng.randint(1, 4), cantidad_gramos=None
        )
        for p in elegidos
    ]
    venta, _c, _a, _l = registrar_venta(
        sesion,
        clave_idempotencia=clave,
        id_turno=turno.id_turno,
        referencia_terminal_pago=None,
        instante_origen=instante,
        renglones=renglones,
    )
    return venta.id_venta


def sembrar() -> dict:
    sembrar_catalogo()  # asegura catálogo y existencia (idempotente)
    sesion = SesionLocal()
    try:
        for nombre in SUCURSALES_DEMO:
            if (
                sesion.execute(
                    select(Sucursal).where(Sucursal.nombre == nombre)
                ).scalar_one_or_none()
                is None
            ):
                raise SystemExit(
                    f"Falta la sucursal «{nombre}»; corre primero rasero.semilla_catalogo."
                )

        rng = random.Random(_SEMILLA)
        turno = _turno_demo(sesion)
        productos = _productos_baratos(sesion)
        ahora = datetime.now(timezone.utc)

        nombres_existentes = {
            n for (n,) in sesion.execute(select(Cliente.nombre)).all() if n is not None
        }

        creados = 0
        con_fuga_perfil = 0
        for indice, nombre in enumerate(_PILA_NOMBRES):
            if nombre in nombres_existentes:
                continue
            perfil_nombre, n_visitas, dias_primera, dias_ultima = _DISTRIBUCION[
                indice % len(_DISTRIBUCION)
            ]
            cliente = registrar_cliente(
                sesion,
                nombre=nombre,
                fecha_nacimiento=_fecha_nacimiento(rng, indice),
            )
            creados += 1
            if perfil_nombre == "fuga_activa":
                con_fuga_perfil += 1

            if n_visitas == 1:
                offsets = [dias_ultima]
            else:
                paso = (dias_primera - dias_ultima) / (n_visitas - 1)
                offsets = [round(dias_primera - paso * i) for i in range(n_visitas)]

            for v, offset in enumerate(offsets):
                instante = ahora - timedelta(days=max(offset, 0), hours=rng.randint(8, 19))
                clave = f"semilla-clientes::{nombre}::{v}::{uuid.uuid5(uuid.NAMESPACE_DNS, nombre + str(v))}"
                id_venta = _una_venta(
                    sesion,
                    turno=turno,
                    productos=productos,
                    rng=rng,
                    instante=instante,
                    clave=clave,
                )
                registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=id_venta)

        tocados = evaluar_fugas_pendientes(sesion)

        from sqlalchemy import func
        from rasero.persistencia.modelos import IntervaloCompra, SenalFuga

        por_estado = dict(
            sesion.execute(
                select(IntervaloCompra.estado, func.count()).group_by(IntervaloCompra.estado)
            ).all()
        )
        fugas_activas = sesion.execute(
            select(func.count()).select_from(SenalFuga).where(SenalFuga.estado == "activa")
        ).scalar_one()

        print(
            f"Clientes sembrados: {creados} nuevos (de {len(_PILA_NOMBRES)}). "
            f"evaluar_fugas_pendientes tocó {tocados}."
        )
        print(f"  intervalo_compra por estado: {por_estado}")
        print(f"  señales de fuga activas en la base: {fugas_activas}")
        return {"clientes_creados": creados, "fugas_activas": fugas_activas}
    finally:
        sesion.close()


if __name__ == "__main__":
    sembrar()
